import asyncio
from abc import ABC, abstractmethod
from typing import Any, Dict

from .exceptions import ServerInvokationException


class InvokeManagerBase(ABC):
    def __init__(self, queue: asyncio.Queue):
        self._queue = queue
        self.invokation_events: Dict[str, asyncio.Event] = {}
        self.invokation_results: Dict[str, Dict[str, Any]] = {}
        self.invokation_exceptions: Dict[str, ServerInvokationException] = {}
        self.total_invokes = 0

    def _create_invokation_id(self) -> str:
        invokation_id = str(self.total_invokes)
        self.total_invokes += 1
        event = asyncio.Event()
        self.invokation_events[invokation_id] = event
        return invokation_id

    async def _invoke_and_wait_for_result(
        self, invokation_id: str, message: Any
    ) -> Dict[str, Any]:
        await self._queue.put(message)
        await self.invokation_events[invokation_id].wait()
        if invokation_id in self.invokation_exceptions:
            raise self.invokation_exceptions.pop(invokation_id)
        return self.invokation_results.pop(invokation_id)

    @abstractmethod
    async def invoke(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        pass

    def set_invokation_result(self, invoke_id: str, result: Any) -> None:
        event = self.invokation_events.pop(invoke_id, None)
        if event is None:
            raise RuntimeError(f"Invokation event {invoke_id} not found")
        self.invokation_results[invoke_id] = result
        event.set()

    def set_invokation_exception(self, invoke_id: str, error_msg: str) -> None:
        event = self.invokation_events.pop(invoke_id, None)
        if event is None:
            raise RuntimeError(f"Invokation event {invoke_id} not found")
        self.invokation_exceptions[invoke_id] = ServerInvokationException(error_msg)
        event.set()
