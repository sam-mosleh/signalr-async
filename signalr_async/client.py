import asyncio
import logging
import time
from abc import ABC, abstractmethod
from types import TracebackType
from typing import Any, Dict, Generic, List, Optional, Set, Type, TypeVar

from .connection import ConnectionBase
from .exceptions import ConnectionClosed, ConnectionInitializationError
from .invoke_manager import InvokeManager
from .messages import InvocationBase

# Type of Invoke message which is in queue
I = TypeVar("I", bound=InvocationBase)
# Type of all Messages received
R = TypeVar("R")


class SignalRClientBase(ABC, Generic[R, I]):
    def __init__(
        self,
        base_url: str,
        timeout: float = 30,
        keepalive_interval: float = 15,
        reconnect_policy: bool = True,
        logger: Optional[logging.Logger] = None,
        connection_options: Optional[Dict[str, Any]] = None,
    ):
        self.logger = logger or logging.getLogger(__name__)
        self.reconnect_policy = reconnect_policy
        self.timeout = timeout
        self.keepalive_interval = keepalive_interval
        self._all_tasks: Set["asyncio.Task[None]"] = set()
        self._producer_queue: "asyncio.Queue[I]" = asyncio.Queue()
        self._invoke_manager = InvokeManager(self._producer_queue)
        self._connection = self.build_connection(base_url, connection_options or {})

    @abstractmethod
    def build_connection(
        self, base_url: str, connection_options: Dict[str, Any]
    ) -> ConnectionBase[R, I]:
        """Build new connection"""

    async def __aenter__(self) -> "SignalRClientBase[R, I]":
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
        if await self._start_connection():
            self._all_tasks.update(
                {
                    asyncio.create_task(self._consumer()),
                    asyncio.create_task(self._producer()),
                    asyncio.create_task(self._timeout_handler()),
                    asyncio.create_task(self._keepalive_handler()),
                }
            )
            # Context switch for tasks
            await asyncio.sleep(0)
            self.logger.debug("Tasks created")
        self.logger.debug("Client started successfully")

    async def stop(self) -> None:
        tasks: List["asyncio.Task[None]"] = []
        if self._all_tasks:
            tasks.extend(self._all_tasks)
            self._all_tasks.clear()
            for task in tasks:
                task.cancel()
        await self._stop_connection()
        if tasks:
            gather = await asyncio.gather(*tasks)
            self.logger.debug(f"{gather=}")

    async def _start_connection(self) -> bool:
        if await self._connection.start():
            await self._connection_event()
            return True
        return False

    async def _stop_connection(self) -> bool:
        if await self._connection.stop():
            self._invoke_manager.cancel_all_pending_invocations("Client disconnected")
            await self._disconnection_event()
            return True
        return False

    @abstractmethod
    async def _connection_event(self) -> None:
        """Inform hub or hubs that client is connected"""

    @abstractmethod
    async def _disconnection_event(self) -> None:
        """Inform hub or hubs that client is disconnected"""

    async def _producer(self) -> None:
        while True:
            try:
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
            except asyncio.CancelledError:
                break

    async def _consumer(self) -> None:
        while True:
            try:
                try:
                    messages = await self._connection.receive()
                    for message in messages:
                        await self._process_message(message)
                except ConnectionClosed:
                    # Receive failure
                    self.logger.debug(f"Consumer state is {self._connection.state}")
                    if self.reconnect_policy:
                        if self._connection.state == "connected":
                            await self._stop_connection()
                        elif self._connection.state == "disconnected":
                            try:
                                await self._start_connection()
                            except ConnectionInitializationError as e:
                                self.logger.exception(e)
                    else:
                        await asyncio.shield(self.stop())
                    await asyncio.sleep(1)
            except asyncio.CancelledError:
                break

    @abstractmethod
    async def _process_message(self, message: R) -> None:
        """Process received messages"""

    async def _timeout_handler(self) -> None:
        timeout_steps = min(self.timeout / 10, 1)
        while True:
            try:
                await asyncio.sleep(timeout_steps)
                if self._connection.last_message_received_time is not None:
                    diff = time.time() - self._connection.last_message_received_time
                    if diff >= self.timeout:
                        self.logger.error("Connection timeout")
                        await self._stop_connection()
                    elif diff >= self.timeout * 0.8:
                        self.logger.warning("No message received in a long time")
            except asyncio.CancelledError:
                break

    async def _keepalive_handler(self) -> None:
        while True:
            try:
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
            except asyncio.CancelledError:
                break

    async def wait(self, timeout: Optional[float] = None) -> None:
        done, pending = await asyncio.wait(
            self._all_tasks, timeout=timeout, return_when=asyncio.FIRST_COMPLETED
        )
        for task in done:
            await task
        if self._all_tasks and done:
            raise RuntimeError("Tasks should be running")
