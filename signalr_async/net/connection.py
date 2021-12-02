import json
import logging
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union

import yarl

from signalr_async.connection import ConnectionBase
from signalr_async.exceptions import (
    ConnectionInitializationError,
    IncompatibleServerError,
)

from .messages import HubInvocation, HubMessage, HubResult

# NegotiationResponse
# {
#     public string ConnectionId { get; set; }
#     public string ConnectionToken { get; set; }
#     public string Url { get; set; }
#     public string ProtocolVersion { get; set; }
#     public double DisconnectTimeout { get; set; }
#     public bool TryWebSockets { get; set; }
#     public double? KeepAliveTimeout { get; set; }
#     public double TransportConnectTimeout { get; set; }

#     // Protocol 2.0: Redirection and custom Negotiation Errors
#     public string RedirectUrl { get; set; }
#     public string AccessToken { get; set; }
#     public string Error { get; set; }
# }


class CommandEnum(str, Enum):
    NEGOTIATE = "negotiate"
    START = "start"
    CONNECT = "connect"
    RECONNECT = "reconnect"
    ABORT = "abort"


class SignalRConnection(ConnectionBase[HubMessage, HubInvocation]):
    client_protocol_version: str = "1.5"

    def __init__(
        self,
        base_url: str,
        hub_names: Optional[List[str]] = None,
        extra_params: Optional[Dict[str, str]] = None,
        extra_headers: Optional[Dict[str, str]] = None,
        logger: Optional[logging.Logger] = None,
    ):
        super().__init__(base_url, extra_params, extra_headers, logger)
        self._hub_names = hub_names or []
        self.transport: Optional[str] = None
        self.message_id: Optional[str] = None
        self.groups_token: Optional[str] = None
        self.keepalive_timeout: Optional[int] = None
        self._ping_message = "{}"

    def _common_params(self) -> Dict[str, str]:
        connection_data = [{"name": hub_name} for hub_name in self._hub_names]
        params = dict(
            clientProtocol=self.client_protocol_version,
            connectionData=json.dumps(connection_data),
            **self._extra_params,
        )
        if self.transport is not None:
            params["transport"] = self.transport
        if self.connection_token is not None:
            params["connectionToken"] = self.connection_token
        return params

    def _receive_params(self) -> Dict[str, str]:
        params = self._common_params()
        if self.message_id is not None:
            params["messageId"] = self.message_id
        if self.groups_token is not None:
            params["groupsToken"] = self.groups_token
        return params

    async def _send_command(self, command: CommandEnum) -> Any:
        if self._session is None:
            raise RuntimeError("Connection is not started")
        async with self._session.get(
            self._base_url / command.value,
            params=self._common_params(),
            headers=self._extra_headers,
        ) as resp:
            resp.raise_for_status()
            return await resp.json()

    async def _negotiate(self) -> None:
        negotiation_response = await self._send_command(CommandEnum.NEGOTIATE)
        self.logger.debug(f"Negotiation response: {negotiation_response}")
        if "availableTransports" in negotiation_response:
            raise IncompatibleServerError("ASP.Net Core server detected")
        if negotiation_response["TryWebSockets"] is False:
            raise IncompatibleServerError(
                "Server does not support websocket as a transport."
            )
        self.transport = "webSockets"
        # TODO: raise IncompatibleServerError in case of bad ProtocolVersion
        self.connection_token = negotiation_response["ConnectionToken"]
        self.connection_id = negotiation_response["ConnectionId"]
        self.keepalive_timeout = negotiation_response.get("KeepAliveTimeout", 5)

    def _generate_receive_path(self, command: CommandEnum) -> yarl.URL:
        if self._base_url.scheme == "http":
            scheme = "ws"
        elif self._base_url.scheme == "https":
            scheme = "wss"
        else:
            raise ValueError(f"Unknown scheme {self._base_url.scheme}")
        return (
            self._base_url.with_scheme(scheme) / command.value % self._receive_params()
        )

    def _generate_connect_path(self) -> yarl.URL:
        return self._generate_receive_path(CommandEnum.CONNECT)

    async def _initialize_connection(self) -> None:
        # TODO: timeout
        # "C": str, S: int, M: List
        first_message = json.loads(await self._receive_raw())
        if "C" in first_message and first_message.get("S", 0) == 1:
            self.message_id = first_message["C"]
            start_response = await self._send_command(CommandEnum.START)
            if start_response["Response"] != "started":
                raise ConnectionInitializationError("Server is not started")
            await self.ping()
        else:
            raise ConnectionInitializationError("Server did not send the start message")

    def _read_message(self, data: Union[str, bytes]) -> List[HubMessage]:
        raw_message: Dict[str, Any] = json.loads(data)
        if "I" in raw_message:
            return [HubResult.from_raw_message(raw_message)]
        message_dict = {
            "message_id": raw_message.get("C"),
            "messages": raw_message.get("M"),
            "initialized": raw_message.get("S"),
            "should_reconnect": raw_message.get("T"),
            "long_poll_delay": raw_message.get("L"),
            "groups_token": raw_message.get("G"),
            "error": raw_message.get("E"),
        }
        if message_dict["error"] is not None:
            # TODO: Close connection with error
            self.logger.error(message_dict["error"])
        if message_dict["groups_token"] is not None:
            self.groups_token = message_dict["groups_token"]
        if message_dict["messages"] is not None:
            self.message_id = message_dict["message_id"]
            return [HubInvocation.from_raw_message(m) for m in message_dict["messages"]]
        elif raw_message:
            self.logger.error(f"Whats this: {raw_message}")
        return []

    def _write_message(self, message: HubInvocation) -> Tuple[Union[str, bytes], bool]:
        return json.dumps(message.to_raw_message()), False

    def _clear_connection_data(self) -> None:
        self.connection_id = None
        self.connection_token = None
        self.groups_token = None
        self.message_id = None

    async def ping(self) -> None:
        return await self._send_raw(self._ping_message, False)
