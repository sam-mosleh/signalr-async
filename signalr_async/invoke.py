import asyncio
from typing import Any, List


class InvokeManager:
    def __init__(self, queue: asyncio.Queue):
        self._queue = queue
        self.invokation_events = {}
        self.invokation_result = {}
        self.total_invokes = 0

    async def invoke(self, hub_name: str, method: str, method_args: List[Any] = []):
        invoke_id = str(self.total_invokes)
        self.total_invokes += 1
        event = asyncio.Event()
        self.invokation_events[invoke_id] = event
        await self._queue.put(
            {"H": hub_name, "M": method, "A": method_args, "I": invoke_id}
        )
        await event.wait()
        return self.invokation_result.pop(invoke_id)

    def set_invokation_result(self, invoke_id: str, result: Any):
        self.invokation_result[invoke_id] = result
        event = self.invokation_events.pop(invoke_id, None)
        if event is None:
            raise RuntimeError(f"Invokation event {invoke_id} not found")
        event.set()
