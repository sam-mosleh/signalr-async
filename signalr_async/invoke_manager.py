import asyncio
from typing import Any, Dict, Generic, TypeVar

from .exceptions import ServerInvocationException
from .messages import InvocationBase

I = TypeVar("I", bound=InvocationBase)


class InvokeManager(Generic[I]):
    def __init__(self, queue: "asyncio.Queue[I]"):
        self._queue = queue
        self.invocation_events: Dict[str, asyncio.Event] = {}
        self.invocation_results: Dict[str, Dict[str, Any]] = {}
        self.invocation_exceptions: Dict[str, ServerInvocationException] = {}
        self.total_invokes = 0

    def next_invocation_id(self) -> str:
        invocation_id = str(self.total_invokes)
        self.total_invokes += 1
        event = asyncio.Event()
        self.invocation_events[invocation_id] = event
        return invocation_id

    async def invoke_and_wait_for_result(self, invocation_id: str, message: I) -> Any:
        await self._queue.put(message)
        await self.invocation_events[invocation_id].wait()
        if invocation_id in self.invocation_exceptions:
            raise self.invocation_exceptions.pop(invocation_id)
        return self.invocation_results.pop(invocation_id)

    def set_invocation_result(self, invocation_id: str, result: Any) -> None:
        event = self.invocation_events.pop(invocation_id, None)
        if event is None:
            raise RuntimeError(f"invocation event {invocation_id} not found")
        self.invocation_results[invocation_id] = result
        event.set()

    def set_invocation_exception(self, invocation_id: str, error_msg: str) -> None:
        event = self.invocation_events.pop(invocation_id, None)
        if event is None:
            raise RuntimeError(f"invocation event {invocation_id} not found")
        self.invocation_exceptions[invocation_id] = ServerInvocationException(error_msg)
        event.set()
