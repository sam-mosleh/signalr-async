import asyncio
from typing import Any, Dict, Generic, TypeVar

from .exceptions import ServerInvocationException
from .messages import InvocationBase

I = TypeVar("I", bound=InvocationBase)


class InvokeManager(Generic[I]):
    def __init__(self, queue: "asyncio.Queue[I]"):
        self._queue = queue
        self.invocation_events: Dict[str, asyncio.Event] = {}
        self.invocation_results: Dict[str, Any] = {}
        self.invocation_exceptions: Dict[str, ServerInvocationException] = {}
        self.total_invokes = 0

    def next_invocation_id(self) -> str:
        invocation_id = str(self.total_invokes)
        self.total_invokes += 1
        event = asyncio.Event()
        self.invocation_events[invocation_id] = event
        return invocation_id

    async def _wait_for(self, invocation_id: str) -> Any:
        if invocation_id not in self.invocation_events:
            raise RuntimeError(f"Invocation {invocation_id} not found")
        await self.invocation_events[invocation_id].wait()
        if invocation_id in self.invocation_exceptions:
            raise self.invocation_exceptions.pop(invocation_id)
        return self.invocation_results.pop(invocation_id)

    async def invoke(self, message: I) -> None:
        return await self._queue.put(message)

    async def invoke_and_wait_for_result(self, invocation_id: str, message: I) -> Any:
        await self.invoke(message)
        result = await self._wait_for(invocation_id)
        self.invocation_events.pop(invocation_id)
        return result

    async def invoke_and_wait_for_stream(self, invocation_id: str, message: I) -> Any:
        self.invocation_results[invocation_id] = []
        await self.invoke(message)
        while True:
            results = await self._wait_for(invocation_id)
            self.invocation_results[invocation_id] = []
            self.invocation_events[invocation_id].clear()
            for result in results:
                if isinstance(result, StopAsyncIteration):
                    return
                yield result

    def set_invocation_result(self, invocation_id: str, result: Any) -> None:
        if invocation_id not in self.invocation_events:
            raise RuntimeError(f"invocation event {invocation_id} not found")
        if isinstance(self.invocation_results.get(invocation_id), list):
            self.invocation_results[invocation_id].append(StopAsyncIteration())
        else:
            self.invocation_results[invocation_id] = result
        self.invocation_events[invocation_id].set()

    def add_invocation_result(self, invocation_id: str, result: Any) -> None:
        if invocation_id not in self.invocation_events:
            raise RuntimeError(f"invocation event {invocation_id} not found")
        if isinstance(self.invocation_results.get(invocation_id), list):
            self.invocation_results[invocation_id].append(result)
            self.invocation_events[invocation_id].set()
        else:
            raise RuntimeError(f"Invocation {invocation_id} is not a stream")

    def set_invocation_exception(self, invocation_id: str, error_msg: str) -> None:
        if invocation_id not in self.invocation_events:
            raise RuntimeError(f"invocation event {invocation_id} not found")
        self.invocation_exceptions[invocation_id] = ServerInvocationException(error_msg)
        self.invocation_events[invocation_id].set()

    def cancel_all_pending_invocations(self, error_msg: str) -> None:
        for invocation_id in self.invocation_events:
            self.set_invocation_exception(invocation_id, error_msg)
