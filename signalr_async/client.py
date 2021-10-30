import asyncio
import logging
import time
from abc import ABC, abstractmethod
from types import TracebackType
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar

from .connection import ConnectionBase
from .exceptions import ConnectionClosed, ConnectionInitializationError
from .invoke_manager import InvokeManagerBase
from .messages import InvocationBase

# Type of hub
H = TypeVar("H")
# Type of Invoke message which is in queue
I = TypeVar("I", bound=InvocationBase)
# Type of all Messages received
R = TypeVar("R")


class SignalRClientBase(ABC, Generic[H, I, R]):
    def __init__(
        self,
        base_url: str,
        hub: H,
        timeout: float = 30,
        keepalive_interval: float = 15,
        reconnect_policy: bool = True,
        logger: Optional[logging.Logger] = None,
        connection_options: Optional[Dict[str, Any]] = None,
    ):
        self._hub = hub
        self.logger = logger or logging.getLogger(__name__)
        self.reconnect_policy = reconnect_policy
        self.timeout = timeout
        self.keepalive_interval = keepalive_interval
        self._producer_queue: "asyncio.Queue" = asyncio.Queue()
        # self._consumer_task: Optional[asyncio.Task] = None
        # self._producer_task: Optional[asyncio.Task] = None
        # self._timeout_task: Optional[asyncio.Task] = None
        # self._keepalive_task: Optional[asyncio.Task] = None
        self._all_tasks: List[asyncio.Task] = []
        self._connection: ConnectionBase[R, I] = self.build_connection(
            base_url, connection_options or {}
        )
        self._invoke_manager = self.build_invoke_manager()

    @abstractmethod
    def build_connection(
        self, base_url: str, connection_options: Dict[str, Any]
    ) -> ConnectionBase:
        """Build new connection"""

    @abstractmethod
    def build_invoke_manager(self) -> InvokeManagerBase:
        """Build invoke manager and connect hubs to it"""

    async def __aenter__(self) -> "SignalRClientBase":
        await self.start()
        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> None:
        await self.stop()

    async def start(self) -> None:
        if await self._connection.start():
            self._all_tasks.extend(
                [
                    asyncio.create_task(self._consumer()),
                    asyncio.create_task(self._producer()),
                    asyncio.create_task(self._timeout_handler()),
                    asyncio.create_task(self._keepalive_handler()),
                ]
            )
            self.logger.debug("Tasks created")
            await self._connection_event()
        self.logger.debug("Client started successfully")

    async def stop(self) -> None:
        if await self._connection.stop():
            await self._disconnection_event()
        for task in self._all_tasks:
            task.cancel()
        gather = await asyncio.gather(*self._all_tasks, return_exceptions=True)
        self.logger.debug(f"{gather=}")
        self._all_tasks.clear()

    @abstractmethod
    async def _connection_event(self) -> None:
        """Inform hub or hubs that client is connected"""

    @abstractmethod
    async def _disconnection_event(self) -> None:
        """Inform hub or hubs that client is disconnected"""

    async def _producer(self) -> None:
        while True:
            message: I = await self._producer_queue.get()
            if message.invocation_id:
                try:
                    await self._connection.send(message)
                except ConnectionClosed:
                    self.logger.error(
                        f"Message has not been sent because connection is closed"
                    )
                    self._invoke_manager.set_invocation_exception(
                        message.invocation_id, "Connection is closed"
                    )

    async def _consumer(self) -> None:
        while True:
            try:
                messages = await self._connection.receive()
                for message in messages:
                    await self._process_message(message)
            except ConnectionClosed:
                # Receive failure
                self.logger.info(f"Consumer state is {self._connection.state}")
                if self.reconnect_policy:
                    if self._connection.state == "connected":
                        await self._connection.stop()
                        await self._disconnection_event()
                    elif self._connection.state == "disconnected":
                        try:
                            await self._connection.start()
                            await self._connection_event()
                        except ConnectionInitializationError as e:
                            self.logger.exception(e)
                else:
                    await asyncio.shield(self.stop())
                await asyncio.sleep(1)
            except Exception as e:
                self.logger.exception(e)
                # await asyncio.sleep(1)
                raise e

    @abstractmethod
    async def _process_message(self, message: R) -> None:
        """Process received messages"""

    async def _timeout_handler(self) -> None:
        timeout_steps = min(self.timeout / 10, 1)
        while True:
            await asyncio.sleep(timeout_steps)
            if self._connection.last_message_received_time is not None:
                diff = time.time() - self._connection.last_message_received_time
                if diff >= self.timeout:
                    self.logger.error("Connection timeout")
                    await self._connection.stop()
                    await self._disconnection_event()
                elif diff >= self.timeout * 0.8:
                    self.logger.warning("No message received in a long time")

    async def _keepalive_handler(self) -> None:
        while True:
            if self._connection.last_message_sent_time is None:
                await asyncio.sleep(1)
            else:
                diff = time.time() - self._connection.last_message_sent_time
                if diff >= self.keepalive_interval:
                    self.logger.debug("Connection keepalive")
                    try:
                        await self._connection.ping()
                    except ConnectionClosed:
                        self.logger.error("Connection keepalive failed to send")
                else:
                    await asyncio.sleep(self.keepalive_interval - diff)
