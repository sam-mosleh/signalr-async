import asyncio
from typing import Any, Dict, List

from .exceptions import ServerInvokationException


class InvokeManager:
    def __init__(self, queue: asyncio.Queue):
        self._queue = queue
        self.invokation_events: Dict[str, asyncio.Event] = {}
        self.invokation_results: Dict[str, Any] = {}
        self.invokation_exceptions: Dict[str, ServerInvokationException] = {}
        self.total_invokes = 0

    async def invoke(self, hub_name: str, method: str, method_args: List[Any] = []):
        invoke_id = str(self.total_invokes)
        self.total_invokes += 1
        event = asyncio.Event()
        self.invokation_events[invoke_id] = event
        await self._queue.put(
            {"I": invoke_id, "H": hub_name, "M": method, "A": method_args}
        )
        await event.wait()
        if invoke_id in self.invokation_exceptions:
            raise self.invokation_exceptions.pop(invoke_id)
        return self.invokation_results.pop(invoke_id)

    def set_invokation_result(self, invoke_id: str, result: Any):
        self.invokation_results[invoke_id] = result
        event = self.invokation_events.pop(invoke_id, None)
        if event is None:
            raise RuntimeError(f"Invokation event {invoke_id} not found")
        event.set()

    def set_invokation_exception(self, invoke_id: str, error_msg: str):
        self.invokation_exceptions[invoke_id] = ServerInvokationException(error_msg)
        event = self.invokation_events.pop(invoke_id, None)
        if event is None:
            raise RuntimeError(f"Invokation event {invoke_id} not found")
        event.set()
