import json
import logging
from typing import Dict, List, Optional, Union, Any, Tuple

import yarl

from signalr_async.connection import ConnectionBase
from signalr_async.exceptions import (
    ConnectionInitializationError,
    IncompatibleServerError,
)

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

# common_params = {"clientProtocol": protocol_version, "transport": transport, "connectionData":hub_names, "connectionToken": connectionToken, **custom}
# Negotiate : url/negotiate + common_params
# Start : url/start + common_params
# Connect: url/connect + receive_params
# Reconnect: url/reconnect + receive_params
# Abort: url/abort + common_params


# ConnectionId = negotiationResponse.ConnectionId;
# ConnectionToken = negotiationResponse.ConnectionToken;
# _disconnectTimeout = TimeSpan.FromSeconds(negotiationResponse.DisconnectTimeout);
# _totalTransportConnectTimeout = TransportConnectTimeout + TimeSpan.FromSeconds(negotiationResponse.TransportConnectTimeout);
# var beatInterval = TimeSpan.FromSeconds(5);
# // If we have a keep alive
# if (negotiationResponse.KeepAliveTimeout != null)
# {
#     _keepAliveData = new KeepAliveData(TimeSpan.FromSeconds(negotiationResponse.KeepAliveTimeout.Value));
#     #_reconnectWindow = _disconnectTimeout + _keepAliveData.Timeout;

#     beatInterval = _keepAliveData.CheckInterval;
# }
# else
# {
#     #_reconnectWindow = _disconnectTimeout;
# }


# // Clear the state for this connection
# ConnectionId = null;
# ConnectionToken = null;
# GroupsToken = null;
# MessageId = null;
# _connectionData = null;
# _actualUrl = _userUrl;
# _actualQueryString = _userQueryString;


class SignalRConnection(ConnectionBase):
    client_protocol_version: str = "1.5"

    def __init__(
        self,
        base_url: str,
        hub_names: Optional[List[str]] = None,
        extra_params: Optional[Dict[str, str]] = None,
        extra_headers: Optional[Dict[str, str]] = None,
        logger: Optional[logging.Logger] = None,
    ):
        super().__init__(base_url, hub_names, extra_params, extra_headers, logger)
        self.transport: Optional[str] = None
        self.message_id: Optional[str] = None
        self.groups_token: Optional[str] = None
        self.keepalive_timeout: Optional[int] = None

    def _common_params(self) -> Dict[str, str]:
        connection_data = [{"name": hub_name} for hub_name in self._hub_names]
        params = dict(
            connectionData=json.dumps(connection_data),
            clientProtocol=self.client_protocol_version,
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

    async def _send_command(self, command: str) -> Any:
        if self._session is None:
            raise RuntimeError("Connection is not started")
        async with self._session.get(
            self._base_url / command,
            params=self._common_params(),
            headers=self._extra_headers,
        ) as resp:
            resp.raise_for_status()
            return await resp.json()

    async def _negotiate(self) -> None:
        negotiation_response = await self._send_command("negotiate")
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
        self.keepalive_timeout = negotiation_response.get("KeepAliveTimeout")

    def _generate_receive_path(self, command: str) -> yarl.URL:
        if self._base_url.scheme == "http":
            scheme = "ws"
        elif self._base_url.scheme == "https":
            scheme = "wss"
        else:
            raise ValueError(f"Unknown scheme {self._base_url.scheme}")
        return self._base_url.with_scheme(scheme) / command % self._receive_params()

    def _generate_connect_path(self) -> yarl.URL:
        return self._generate_receive_path("connect")

    async def _initialize_connection(self) -> None:
        # TODO: timeout
        first_message = await self.receive()
        if first_message.get("S", 0) == 1:
            start_response = await self._send_command("start")
            if start_response["Response"] != "started":
                raise ConnectionInitializationError("Server is not started")
        else:
            raise ConnectionInitializationError("Server did not send the start message")

    def _read_message(self, data: Union[str, bytes]) -> Dict[str, Any]:
        raw_message: Dict[str, Any] = json.loads(data)
        if "G" in raw_message:
            self.groups_token = raw_message["G"]
        if "M" in raw_message:
            self.message_id = raw_message["C"]
        return raw_message

    def _write_message(self, message: Dict[str, Any]) -> Tuple[Union[str, bytes], bool]:
        return json.dumps(message), False

    async def _clear_connection_data(self) -> None:
        self.connection_id = None
        self.connection_token = None
        self.groups_token = None
        self.message_id = None

    async def ping(self) -> None:
        return await self.send({})
