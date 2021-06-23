import asyncio
import datetime
import json
import logging
from typing import List, Optional
from urllib.parse import urlencode, urlparse

import aiohttp
import websockets
from websockets.exceptions import WebSocketException

from .exceptions import (
    ConnectionInitializationError,
    ConnectionStartError,
    IncompatibleServerError,
)


class Connection:
    def __init__(
        self,
        url: str,
        hub_names: List[str] = [],
        extra_params: dict = {},
        logger: Optional[logging.Logger] = None,
    ):
        self.url = url
        self.hub_names = hub_names
        self.extra_params = extra_params
        self.logger = logger or logging.getLogger(__name__)
        self.last_message_time: datetime.datetime = None
        self.transport = None
        self.connection_id = None
        self.connection_token = None
        self.message_id = None
        self.groups_token = None
        self.beat_task: asyncio.Task = None
        self.keepalive_timeout = None
        self.client_protocol_version = "1.5"
        self.session = aiohttp.ClientSession()
        self.state = "DISCONNECTED"

    async def start(self):
        try:
            self.state = "CONNECTING"
            await self._send_negotiate_command()
            self.websocket = await websockets.connect(self._connect_path)
            await self._initialize_connection()
            self.beat_task = asyncio.create_task(self._beat(self.keepalive_timeout))
            self.state = "CONNECTED"
        except (
            aiohttp.ClientError,
            WebSocketException,
            OSError,
        ) as e:
            self.state = "DISCONNECTED"
            await self.session.close()
            raise ConnectionInitializationError("Connection to server failed") from e
        except ConnectionStartError as e:
            self.state = "DISCONNECTED"
            await self.websocket.close()
            await self.session.close()
            raise ConnectionInitializationError(
                "Connection to server failed to initialize"
            ) from e

    async def close(self):
        if self.state not in ("DISCONNECTED", "DISCONNECTING"):
            self.state = "DISCONNECTING"
            self.logger.info("Closing SignalR connection")
            if self.beat_task is not None:
                self.beat_task.cancel()
                self.beat_task = None
            await self.websocket.close()
            await self.session.close()
            self.state = "DISCONNECTED"

    @property
    def _common_params(self):
        connection_data = [{"name": hub_name} for hub_name in self.hub_names]
        params = dict(
            connectionData=json.dumps(connection_data),
            clientProtocol=self.client_protocol_version,
            **self.extra_params,
        )
        if self.transport is not None:
            params["transport"] = self.transport
        if self.connection_token is not None:
            params["connectionToken"] = self.connection_token
        return params

    @property
    def _receive_params(self):
        params = self._common_params
        if self.message_id is not None:
            params["messageId"] = self.message_id
        if self.groups_token is not None:
            params["groupsToken"] = self.groups_token
        return params

    @property
    def _connect_path(self) -> str:
        parsed_url = urlparse(self.url)
        if parsed_url.scheme == "http":
            parsed_url = parsed_url._replace(scheme="ws")
        else:
            parsed_url = parsed_url._replace(scheme="wss")
        return parsed_url.geturl() + "/connect?" + urlencode(self._receive_params)

    async def _send_command(self, command: str):
        async with self.session.get(
            self.url + command, params=self._common_params
        ) as resp:
            resp.raise_for_status()
            return await resp.json()

    async def _send_negotiate_command(self):
        self.logger.debug("Negotiation started")
        return await self._complete_negotiation(await self._send_command("/negotiate"))

    async def _complete_negotiation(self, negotiation_response):
        if "availableTransports" in negotiation_response:
            raise IncompatibleServerError("ASP.Net Core server detected")
        if negotiation_response["TryWebSockets"] is False:
            raise IncompatibleServerError(
                "Server doesnt support websocket as a transport."
            )
        # TODO: raise IncompatibleServerError in case of bad ProtocolVersion
        self.connection_token = negotiation_response["ConnectionToken"]
        self.connection_id = negotiation_response["ConnectionId"]
        self.keepalive_timeout = negotiation_response.get("KeepAliveTimeout")
        # self.beat_interval = keepalive_timeout or 5
        # if keepalive_timeout is not None:
        #     self.beat_task = asyncio.create_task(self._beat(keepalive_timeout))
        # disconnect_timeout = negotiation_response["DisconnectTimeout"]
        # self.reconnect_window = disconnect_timeout + (self.keepalive_timeout or 0)
        self.transport = "webSockets"

    async def _send_start_command(self):
        self.logger.debug("Initialization started")
        return self._complete_start(await self._send_command("/start"))

    def _complete_start(self, start_response):
        if start_response["Response"] != "started":
            raise ConnectionStartError("Server didnt start")

    async def _beat(self, keepalive_timeout: int):
        keepalive_warning_timeout = keepalive_timeout * 2 / 3
        while True:
            await asyncio.sleep(1)
            elapsed_seconds = (
                datetime.datetime.now() - self.last_message_time
            ).total_seconds()
            if elapsed_seconds >= keepalive_timeout:
                self.logger.error("Connection is dead")
                await asyncio.shield(self.close())
            elif elapsed_seconds >= keepalive_warning_timeout:
                self.logger.warn("Connection might be dead or slow")

    async def receive(self) -> dict:
        response = await self.websocket.recv()
        data = json.loads(response)
        self._process_connection_data(data)
        return data

    async def send(self, data: dict):
        return await self.websocket.send(json.dumps(data))

    async def _initialize_connection(self):
        first_message = await self.receive()
        if first_message.get("S", 0) == 1:
            await self._send_start_command()
        else:
            raise ConnectionStartError("Server didnt send start message")

    # async def _consumer(self):
    #     while True:
    #         message = await self.recv()
    #         self.logger.debug(f"Connection message: {message}")
    #         if message:
    #             try:
    #                 await self._process_connection_data(message)
    #             except Exception as e:
    #                 self.logger.exception(str(e))

    def _process_connection_data(self, message: dict):
        # if "I" in message:
        #     await self.queue.put(message)
        # else:
        #     if "E" in message:
        #         error_message = message["E"]
        #         raise RuntimeError(f"Error from server: {error_message}")
        #     if "G" in message:
        #         self.groups_token = message["G"]
        #     if "M" in message:
        #         self.message_id = message["C"]
        #         for client_message in message["M"]:
        #             await self.queue.put(client_message)
        #     if message.get("S"):
        #         self._complete_start(await self._send_start_command())
        self.last_message_time = datetime.datetime.now()
        if "G" in message:
            self.groups_token = message["G"]
        if "M" in message:
            self.message_id = message["C"]
