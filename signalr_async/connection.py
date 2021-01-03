import asyncio
import json
import logging
from typing import List, Optional
from urllib.parse import urlencode, urlparse

import aiohttp
import websockets


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
        self.transport = None
        self.connection_id = None
        self.connection_token = None
        self.message_id = None
        self.groups_token = None
        self.client_protocol_version = "1.5"
        self.session = aiohttp.ClientSession()
        self.queue = asyncio.Queue()
        self._consumer_task = None
        self._start_event = asyncio.Event()

    async def start(self):
        self._complete_negotiation(await self._send_negotiate_command())
        self.websocket = await websockets.connect(self._connect_path)
        self._consumer_task = asyncio.create_task(self._consumer())
        await self._start_event.wait()

    async def close(self):
        self._consumer_task.cancel()
        await self.websocket.close()
        await self.session.close()

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
    def _recieve_params(self):
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
        return parsed_url.geturl() + "/connect?" + urlencode(self._recieve_params)

    async def _send_negotiate_command(self):
        return await self._send_command("/negotiate")

    async def _send_start_command(self):
        response = await self._send_command("/start")
        self._start_event.set()
        return response

    async def _send_command(self, command: str):
        async with self.session.get(
            self.url + command, params=self._common_params
        ) as resp:
            resp.raise_for_status()
            return await resp.json()

    def _complete_negotiation(self, negotiation_response):
        if "availableTransports" in negotiation_response:
            raise RuntimeError("ASP.Net Core server detected")
        if negotiation_response["TryWebSockets"] is False:
            raise RuntimeError("Server doesnt support websocket as a transport.")
        # TODO: save timeouts
        self.connection_id = negotiation_response["ConnectionId"]
        self.connection_token = negotiation_response["ConnectionToken"]
        self.transport = "webSockets"

    def _complete_start(self, start_response):
        if start_response["Response"] != "started":
            raise RuntimeError("Server didnt start")

    async def recv(self) -> dict:
        response = await self.websocket.recv()
        return json.loads(response)

    async def send(self, data: dict):
        return await self.websocket.send(json.dumps(data))

    async def _consumer(self):
        while True:
            message = await self.recv()
            self.logger.debug(f"Connection message: {message}")
            if message:
                try:
                    await self._process_message(message)
                except Exception as e:
                    self.logger.exception(str(e))

    async def _process_message(self, message: dict):
        if "I" in message:
            await self.queue.put(message)
        elif "E" in message:
            error_message = message["E"]
            raise RuntimeError(f"Error from server: {error_message}")
        else:
            message.get("T", 0)
            if "G" in message:
                self.groups_token = message["G"]
            if "M" in message:
                self.message_id = message["C"]
                for client_message in message["M"]:
                    await self.queue.put(client_message)
                if message.get("S"):
                    self._complete_start(await self._send_start_command())
