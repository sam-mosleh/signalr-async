import asyncio
import logging
import time
from abc import ABC, abstractmethod
from types import TracebackType
from typing import Any, Dict, Generic, List, Optional, Sequence, Type, TypeVar, Union

from .connection import ConnectionBase
from .exceptions import ConnectionClosed, ConnectionInitializationError
from .hub import HubBase
from .invoke_manager import InvokeManager
from .messages import InvocationBase

# Type of Invoke message which is in queue
I = TypeVar("I", bound=InvocationBase)
# Type of hub
# H = TypeVar("H")
H = TypeVar("H", bound=Union[HubBase[Any], Sequence[HubBase[Any]]])
# Type of all Messages received
R = TypeVar("R")


class SignalRClientBase(ABC, Generic[H, R, I]):
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
        self._all_tasks: List["asyncio.Task[None]"] = []
        self._producer_queue: "asyncio.Queue[I]" = asyncio.Queue()
        self._invoke_manager = InvokeManager(self._producer_queue)
        self._connection = self.build_connection(base_url, connection_options or {})
        if isinstance(self._hub, Sequence):
            for h in self._hub:
                h._set_invoke_manager(self._invoke_manager)._set_logger(self.logger)
        else:
            self._hub._set_invoke_manager(self._invoke_manager)._set_logger(self.logger)

    @abstractmethod
    def build_connection(
        self, base_url: str, connection_options: Dict[str, Any]
    ) -> ConnectionBase[R, I]:
        """Build new connection"""

    async def __aenter__(self) -> "SignalRClientBase[H, R, I]":
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
        self._all_tasks.clear()
        self.logger.debug(f"{gather=}")

    @abstractmethod
    async def _connection_event(self) -> None:
        """Inform hub or hubs that client is connected"""

    @abstractmethod
    async def _disconnection_event(self) -> None:
        """Inform hub or hubs that client is disconnected"""

    async def _producer(self) -> None:
        while True:
            message = await self._producer_queue.get()
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
