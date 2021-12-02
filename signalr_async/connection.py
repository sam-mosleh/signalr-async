import logging
import time
from abc import abstractmethod
from typing import Dict, Generic, List, Optional, Tuple, TypeVar, Union

import aiohttp
import yarl

from signalr_async.exceptions import ConnectionClosed, ConnectionInitializationError

T = TypeVar("T")
O = TypeVar("O")


class ConnectionBase(Generic[T, O]):
    def __init__(
        self,
        base_url: str,
        extra_params: Optional[Dict[str, str]] = None,
        extra_headers: Optional[Dict[str, str]] = None,
        logger: Optional[logging.Logger] = None,
    ):
        self._base_url = yarl.URL(base_url)
        self._extra_params = extra_params or {}
        self._extra_headers = extra_headers or {}
        self.logger = logger or logging.getLogger(__name__)
        self.last_message_received_time: Optional[float] = None
        self.last_message_sent_time: Optional[float] = None
        self._session: Optional[aiohttp.ClientSession] = None
        self._websocket: Optional[aiohttp.ClientWebSocketResponse] = None
        self.connection_id: Optional[str] = None
        self.connection_token: Optional[str] = None
        self.state = "disconnected"

    async def start(self) -> bool:
        self.logger.debug(f"Starting connection with {self.state} state")
        if self.state == "disconnected":
            try:
                self.state = "connecting"
                self._session = aiohttp.ClientSession()
                self.logger.debug("Negotiation started")
                await self._negotiate()
                connect_path = self._generate_connect_path()
                self.logger.debug(f"Connecting to {connect_path}")
                self._websocket = await self._session.ws_connect(
                    connect_path, headers=self._extra_headers
                )
                self.logger.debug("Initializing")
                await self._initialize_connection()
                self.state = "connected"
                return True
            except aiohttp.client_exceptions.ClientError as e:
                self.logger.debug("Starting connection failed")
                await self.stop()
                raise ConnectionInitializationError("Client cannot connect") from e
            except ConnectionInitializationError:
                self.logger.debug("initialize connection failed")
                await self.stop()
                raise
        return False

    @abstractmethod
    async def _negotiate(self) -> None:
        """Negotiation with server"""

    @abstractmethod
    def _generate_connect_path(self) -> yarl.URL:
        """Build connection path to the server websocket"""

    @abstractmethod
    async def _initialize_connection(self) -> None:
        """Initialize the connection through handshakes and wait for server to get started"""

    async def stop(self) -> bool:
        self.logger.debug(f"Stopping connection with {self.state} state")
        if self.state not in ("disconnecting", "disconnected"):
            self.state = "disconnecting"
            self._clear_connection_data()
            if self._websocket is not None:
                await self._websocket.close()
                self._websocket = None
                self.logger.debug("Websocket closed")
            if self._session is not None:
                await self._session.close()
                self._session = None
                self.logger.debug("Session closed")
            self.last_message_received_time = None
            self.last_message_sent_time = None
            self.state = "disconnected"
            return True
        return False

    def _clear_connection_data(self) -> None:
        pass

    async def _receive_raw(self, timeout: Optional[float] = None) -> Union[str, bytes]:
        if self._websocket is None:
            raise ConnectionClosed() from None
        raw_ws_message = await self._websocket.receive(timeout=timeout)
        self.logger.debug(f"Raw message received: {raw_ws_message}")
        if raw_ws_message.type in (
            aiohttp.WSMsgType.CLOSE,
            aiohttp.WSMsgType.CLOSING,
            aiohttp.WSMsgType.CLOSED,
        ):
            raise ConnectionClosed(raw_ws_message.data, raw_ws_message.extra) from None
        self.last_message_received_time = time.time()
        return raw_ws_message.data  # type: ignore

    async def receive(self, timeout: Optional[float] = None) -> List[T]:
        return self._read_message(await self._receive_raw(timeout=timeout))

    async def _send_raw(
        self, message_content: Union[str, bytes], is_binary: bool
    ) -> None:
        self.logger.debug(f"Sending: {message_content=}, {is_binary=}")
        if self._websocket is None:
            raise ConnectionClosed() from None
        try:
            await self._websocket._writer.send(
                message_content, is_binary, compress=None
            )
            self.last_message_sent_time = time.time()
        except ConnectionResetError as e:
            raise ConnectionClosed() from e

    async def send(self, message: O) -> None:
        return await self._send_raw(*self._write_message(message))

    @abstractmethod
    def _read_message(self, data: Union[str, bytes]) -> List[T]:
        """Parse messages from raw format transferred to client by the server"""

    @abstractmethod
    def _write_message(self, message: O) -> Tuple[Union[str, bytes], bool]:
        """Write message to be transferable and indicate that the output is binary or not"""

    @abstractmethod
    async def ping(self) -> None:
        """Send ping message to the server"""
