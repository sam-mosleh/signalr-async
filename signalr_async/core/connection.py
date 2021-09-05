from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Awaitable, Callable, Dict, Optional
from urllib.parse import urlencode, urlparse

import aiohttp

from signalr_async.core.messages import (
    HubMessage,
    InvocationMessage,
    MessageTypes,
    PingMessage,
)
from signalr_async.core.protocols import JsonProtocol, ProtocolBase
from signalr_async.invoke import InvokeManager as BaseInvokeManager


class SignalRCoreBaseException(Exception):
    pass


class ConnectionClosed(SignalRCoreBaseException):
    def __init__(self, code: Optional[int] = None, reason: Optional[str] = None):
        if code:
            super().__init__(f"Connection closed with code={code}: {reason}")
        else:
            super().__init__("Connection closed")


class HandshakeFailure(SignalRCoreBaseException):
    pass


class InvokeManager(BaseInvokeManager):
    async def invoke(self, method: str, method_args: List[Any] = []):
        invokation_id = self._create_invokation_id()
        message = InvocationMessage(
            invocation_id=invokation_id, target=method, arguments=method_args
        )
        return await self._invoke_and_wait_for_result(invokation_id, message)


class Connection:
    negotiate_version: str = "1"

    def __init__(
        self,
        url: str,
        hub_name: str,
        extra_headers: Dict[str, Any] = {},
        extra_params: Dict[str, Any] = {},
        protocol: ProtocolBase = None,
        logger: Optional[logging.Logger] = None,
    ):
        self.url = url + hub_name if url.endswith("/") else f"{url}/{hub_name}"
        self.extra_headers = extra_headers
        self.extra_params = extra_params
        self.protocol = protocol or JsonProtocol()
        self.handshake_protocol = JsonProtocol()
        self.logger = logger or logging.getLogger(__name__)
        self.connection_id: Optional[str] = None
        self.websocket: Optional[aiohttp.ClientWebSocketResponse] = None
        self.session: Optional[aiohttp.ClientSession] = None

    async def start(self):
        self.session = aiohttp.ClientSession()
        negotiation_response = await self.negotiate()
        self.logger.debug(f"Negotiation response: {negotiation_response}")
        self.connection_id = negotiation_response["connectionId"]
        connect_path = self._connect_path(
            self.url, negotiation_response.get("connectionToken", self.connection_id)
        )
        self.logger.debug(f"Connecting to {connect_path}")
        self.websocket = await self.session.ws_connect(
            connect_path, headers=self.extra_headers
        )
        self.logger.debug(
            f"Handshake using protocol={self.protocol.name}, version={self.protocol.version}"
        )
        await self.websocket.send_str(self.protocol.handshake_params)
        return self.evaluate_handshake(await self.websocket.receive())

    async def stop(self):
        self.connection_id = None
        if self.websocket is not None:
            await self.websocket.close()
            self.websocket = None
            self.logger.debug("Websocket closed")
        if self.session is not None:
            await self.session.close()
            self.session = None
            self.logger.debug("Session closed")

    async def negotiate(self):
        # TODO: handle redirects
        self.logger.debug(f"Negotiation started")
        async with self.session.post(
            self.url + "/negotiate",
            headers=self.extra_headers,
            params={"negotiateVersion": self.negotiate_version},
        ) as resp:
            self.logger.debug(f"Negotiation completed from {resp.url}")
            resp.raise_for_status()
            return await resp.json()

    def _connect_path(self, url: str, connection_id: str) -> str:
        parsed_url = urlparse(url)
        if parsed_url.scheme == "http":
            parsed_url = parsed_url._replace(scheme="ws")
        else:
            parsed_url = parsed_url._replace(scheme="wss")
        parsed_url = parsed_url._replace(query=urlencode({"id": connection_id}))
        return parsed_url.geturl()

    def evaluate_handshake(self, handshake_message: aiohttp.WSMessage):
        if handshake_message.type in (
            aiohttp.WSMsgType.CLOSE,
            aiohttp.WSMsgType.CLOSED,
        ):
            raise HandshakeFailure("Connection is closed")
        elif handshake_message.type not in (
            aiohttp.WSMsgType.TEXT,
            aiohttp.WSMsgType.BINARY,
        ):
            raise HandshakeFailure(f"Unknown handshake received: {handshake_message}")
        data = (
            handshake_message.data
            if handshake_message.type == aiohttp.WSMsgType.TEXT
            else handshake_message.data.decode("utf-8")
        )
        handshake_result = self.handshake_protocol.decode(data)[0]
        if "error" in handshake_result:
            raise HandshakeFailure(handshake_result["error"])

    async def receive(self, timeout: Optional[float] = None):
        if self.websocket is None:
            raise ConnectionClosed() from None
        raw_ws_message = await self.websocket.receive(timeout=timeout)
        self.logger.debug(f"Raw message received: {raw_ws_message}")
        if raw_ws_message.type in (
            aiohttp.WSMsgType.CLOSE,
            aiohttp.WSMsgType.CLOSING,
            aiohttp.WSMsgType.CLOSED,
        ):
            raise ConnectionClosed(raw_ws_message.data, raw_ws_message.extra) from None
        elif raw_ws_message.type not in (
            aiohttp.WSMsgType.TEXT,
            aiohttp.WSMsgType.BINARY,
        ):
            raise Exception("Unknown websocket message type") from None
        return list(self.protocol.parse(raw_ws_message.data))

    async def send(self, message: HubMessage):
        if self.websocket is None:
            raise ConnectionClosed() from None
        message_content = self.protocol.write(message)
        self.logger.debug(f"Sending: {message_content.__repr__()}")
        try:
            return await self.websocket._writer.send(
                message_content, self.protocol.is_binary, compress=None
            )
        except ConnectionResetError as e:
            raise ConnectionClosed() from e


class SignalRCoreClient:
    def __init__(
        self,
        url: str,
        hub_name: str,
        extra_headers: Dict[str, Any] = {},
        extra_params: Dict[str, Any] = {},
        protocol: Optional[ProtocolBase] = None,
        timeout: float = 30,
        keepalive_interval: float = 15,
        reconnect_policy: bool = True,
        logger: Optional[logging.Logger] = None,
    ):
        self.logger = logger or logging.getLogger(__name__)
        self.reconnect_policy = reconnect_policy
        self.timeout = timeout
        self.keepalive_interval = keepalive_interval
        self._connection = Connection(
            url=url,
            hub_name=hub_name,
            extra_headers=extra_headers,
            extra_params=extra_params,
            protocol=protocol,
            logger=self.logger,
        )
        self._producer_queue = asyncio.Queue()
        self._invoke_manager = InvokeManager(self._producer_queue)
        self._consumer_task: asyncio.Task = None
        self._producer_task: asyncio.Task = None
        self._timeout_task: asyncio.Task = None
        self._keepalive_task: asyncio.Task = None
        self._last_message_received_time: float = None
        self._last_message_sent_time: float = None
        self._tasks_running: bool = False
        self.state = "disconnected"
        self._callbacks = {"connect": None}

    async def __aenter__(self) -> SignalRCoreClient:
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.stop()
        print(
            "GATHER",
            await asyncio.gather(
                self._consumer_task, self._producer_task, return_exceptions=True
            ),
        )

    async def _consumer(self):
        while True:
            try:
                messages = await self._connection.receive()
                for message in messages:
                    await self._process_message(message)
            except ConnectionClosed:
                print(f"Consumer connection is closed with state={self.state}")
                if self.reconnect_policy:
                    if self.state == "connected":
                        await self._safe_connection_stop()
                    elif self.state == "disconnected":
                        try:
                            await self._safe_connection_start()
                        except aiohttp.client_exceptions.ClientError as e:
                            self.logger.exception(e)
                else:
                    await asyncio.shield(self.stop())
                await asyncio.sleep(1)
            except Exception as e:
                self.logger.exception(e)
                await asyncio.sleep(1)

    async def _producer(self):
        while True:
            message: HubMessage = await self._producer_queue.get()
            try:
                await self._connection.send(message)
                self._last_message_sent_time = time.time()
            except ConnectionClosed:
                self.logger.error(
                    f"Message has not been sent because connection is closed"
                )
                if message.type_ == MessageTypes.INVOCATION:
                    self._invoke_manager.set_invokation_exception(
                        message.invocation_id, "Connection is closed"
                    )

    async def _timeout_handler(self):
        while True:
            await asyncio.sleep(1)
            if self._last_message_received_time is not None:
                diff = time.time() - self._last_message_received_time
                if diff >= self.timeout:
                    self.logger.error("Connection timeout")
                    await self._safe_connection_stop()
                elif diff >= self.timeout * 0.8:
                    self.logger.warning("No message received in a long time")

    async def _keepalive_handler(self):
        while True:
            if self._last_message_sent_time is None:
                await asyncio.sleep(1)
            else:
                diff = time.time() - self._last_message_sent_time
                if diff >= self.keepalive_interval:
                    self.logger.debug("Connection keepalive")
                    await self._producer_queue.put(PingMessage())
                    # Context switch for sending
                    await asyncio.sleep(0)
                else:
                    await asyncio.sleep(self.keepalive_interval - diff)

    async def start(self):
        if await self._safe_connection_start():
            self.logger.debug("Create tasks")
            self._consumer_task = asyncio.create_task(self._consumer())
            self._producer_task = asyncio.create_task(self._producer())
            self._timeout_task = asyncio.create_task(self._timeout_handler())
            # self._keepalive_task = asyncio.create_task(asyncio.sleep(100))
            self._keepalive_task = asyncio.create_task(self._keepalive_handler())
            self._tasks_running = True
        self.logger.debug("Client started successfully")

    async def _safe_connection_start(self) -> bool:
        self.logger.debug(f"Starting connection with state={self.state}")
        if self.state == "disconnected":
            self.state = "connecting"
            try:
                await self._connection.start()
                self.state = "connected"
                self._last_message_received_time = time.time()
                self._last_message_sent_time = time.time()
                if self._callbacks["connect"]:
                    asyncio.create_task(
                        self._callbacks["connect"](self._connection.connection_id)
                    )
                return True
            except aiohttp.client_exceptions.ClientError:
                self.logger.debug("Starting connection failed")
                await self._safe_connection_stop()
                raise

    async def _safe_connection_stop(self) -> bool:
        self.logger.debug(f"Stopping connection with state={self.state}")
        if self.state not in ("disconnecting", "disconnected"):
            self.state = "disconnecting"
            await self._connection.stop()
            self.state = "disconnected"
            self._last_message_received_time = None
            self._last_message_sent_time = None
            return True
        return False

    async def stop(self):
        await self._safe_connection_stop()
        if self._tasks_running:
            self.logger.info("Cancelling client tasks")
            self._keepalive_task.cancel()
            self._timeout_task.cancel()
            self._producer_task.cancel()
            self._consumer_task.cancel()
            self._tasks_running = False

    async def _process_message(self, message: HubMessage):
        self._last_message_received_time = time.time()
        if message.type_ == MessageTypes.INVOCATION:
            callback = self._callbacks.get(message.target, None)
            if callback is None:
                self.logger.warning(f"Callback {message.target} is not set")
            else:
                asyncio.create_task(callback(*message.arguments))
        elif message.type_ == MessageTypes.STREAM_ITEM:
            pass
        elif message.type_ == MessageTypes.COMPLETION:
            if message.error:
                self._invoke_manager.set_invokation_exception(
                    message.invocation_id, message.error
                )
            else:
                self._invoke_manager.set_invokation_result(
                    message.invocation_id, message.error
                )
        elif message.type_ == MessageTypes.STREAM_INVOCATION:
            pass
        elif message.type_ == MessageTypes.CANCEL_INVOCATION:
            pass
        elif message.type_ == MessageTypes.PING:
            self.logger.debug("[PING]")
        elif message.type_ == MessageTypes.CLOSE:
            if message.error:
                self.logger.error(f"Server closed with reason: {message.error}")
            if message.allow_reconnect:
                await self._safe_connection_stop()
            else:
                await asyncio.shield(self.stop())
        else:
            raise Exception("Unknown message type")

    def on(self, name: str, func: Callable[..., Awaitable[None]]):
        self._callbacks[name] = func

    async def invoke(self, method: str, *args):
        return await self._invoke_manager.invoke(method, args)
