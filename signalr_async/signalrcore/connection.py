import logging
from typing import Dict, Optional, Any, List, Union, Tuple


import yarl

from signalr_async.connection import ConnectionBase
from signalr_async.exceptions import HandshakeError

from .messages import PingMessage, HubMessage
from .protocols import JsonProtocol, ProtocolBase


# TODO: select transferables instead of all HubMessages
class SignalRCoreConnection(ConnectionBase[HubMessage, HubMessage]):
    negotiate_version: str = "1"

    def __init__(
        self,
        base_url: str,
        hub_name: str,
        protocol: Optional[ProtocolBase] = None,
        extra_params: Optional[Dict[str, str]] = None,
        extra_headers: Optional[Dict[str, str]] = None,
        logger: Optional[logging.Logger] = None,
    ):
        super().__init__(base_url, [hub_name], extra_params, extra_headers, logger)
        self._url = self._base_url / hub_name
        self.protocol: ProtocolBase = protocol or JsonProtocol()
        self.handshake_protocol = JsonProtocol()

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

    async def _clear_connection_data(self) -> None:
        self.connection_id = None
        self.connection_token = None

    def _read_message(self, data: Union[str, bytes]) -> List[HubMessage]:
        return list(self.protocol.parse(data))

    def _write_message(self, message: HubMessage) -> Tuple[Union[str, bytes], bool]:
        return self.protocol.write(message), self.protocol.is_binary

    async def ping(self) -> None:
        return await self.send(PingMessage())
