import logging
from typing import Any, Dict, List, Optional, Tuple, Union

import yarl

from signalr_async.connection import ConnectionBase
from signalr_async.exceptions import HandshakeError

from .messages import HubInvocableMessage, HubMessage, PingMessage
from .protocols import JsonProtocol, MessagePackProtocol


class SignalRCoreConnection(ConnectionBase[HubMessage, HubInvocableMessage]):
    negotiate_version: str = "1"

    def __init__(
        self,
        base_url: str,
        hub_name: str,
        protocol: Optional[Union[JsonProtocol, MessagePackProtocol]] = None,
        extra_params: Optional[Dict[str, str]] = None,
        extra_headers: Optional[Dict[str, str]] = None,
        logger: Optional[logging.Logger] = None,
    ):
        super().__init__(base_url, extra_params, extra_headers, logger)
        self._url = self._base_url / hub_name
        self.protocol = protocol or JsonProtocol()
        self.handshake_protocol = JsonProtocol()
        self._ping_message = self.protocol.write(PingMessage())

    def _common_params(self) -> Dict[str, str]:
        params = self._extra_params.copy()
        if self.connection_token:
            params["id"] = self.connection_token
        return params

    async def _send_command(
        self, command: str, params: Optional[Dict[str, str]] = None
    ) -> Any:
        if self._session is None:
            raise RuntimeError("Connection is not started")
        async with self._session.post(
            self._url / command,
            params=params or self._common_params(),
            headers=self._extra_headers,
        ) as resp:
            resp.raise_for_status()
            return await resp.json()

    async def _negotiate(self) -> None:
        negotiation_response = await self._send_command(
            "negotiate", params={"negotiateVersion": self.negotiate_version}
        )
        self.logger.debug(f"Negotiation response: {negotiation_response}")
        self.connection_id = negotiation_response["connectionId"]
        self.connection_token = negotiation_response.get(
            "connectionToken", self.connection_id
        )

    def _generate_connect_path(self) -> yarl.URL:
        if self._url.scheme == "http":
            scheme = "ws"
        elif self._url.scheme == "https":
            scheme = "wss"
        else:
            raise ValueError(f"Unknown scheme {self._url.scheme}")
        return self._url.with_scheme(scheme) % self._common_params()

    async def _initialize_connection(self) -> None:
        await self._send_raw(self.protocol.handshake_params, False)
        # TODO: timeout
        message = await self._receive_raw()
        handshake_result = list(
            self.handshake_protocol.decode(
                message.decode() if isinstance(message, bytes) else message
            )
        )[0]
        self.logger.debug(f"Handshake: {handshake_result}")
        if "error" in handshake_result:
            raise HandshakeError(handshake_result["error"])

    def _clear_connection_data(self) -> None:
        self.connection_id = None
        self.connection_token = None

    def _read_message(self, data: Union[str, bytes]) -> List[HubMessage]:
        # TODO: use self.protocol.is_binary instead of isinstance
        if isinstance(data, str) and isinstance(self.protocol, JsonProtocol):
            return list(self.protocol.parse(data))
        elif isinstance(data, bytes) and isinstance(self.protocol, MessagePackProtocol):
            return list(self.protocol.parse(data))
        else:
            raise RuntimeError(
                f"Protocol type is not respected. Got {type(data)}, expected {self.protocol.transfer_format}"
            )

    def _write_message(self, message: HubMessage) -> Tuple[Union[str, bytes], bool]:
        return self.protocol.write(message), self.protocol.is_binary

    async def ping(self) -> None:
        return await self._send_raw(self._ping_message, self.protocol.is_binary)
