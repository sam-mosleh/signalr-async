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

    def _create_invokation_id(self) -> str:
        invokation_id = str(self.total_invokes)
        self.total_invokes += 1
        event = asyncio.Event()
        self.invokation_events[invokation_id] = event
        return invokation_id

    async def _invoke_and_wait_for_result(self, invokation_id: str, message: Any):
        await self._queue.put(message)
        await self.invokation_events[invokation_id].wait()
        if invokation_id in self.invokation_exceptions:
            raise self.invokation_exceptions.pop(invokation_id)
        return self.invokation_results.pop(invokation_id)

    async def invoke(self, hub_name: str, method: str, method_args: List[Any] = []):
        invokation_id = self._create_invokation_id()
        message = {"I": invokation_id, "H": hub_name, "M": method, "A": method_args}
        return await self._invoke_and_wait_for_result(invokation_id, message)

    def set_invokation_result(self, invoke_id: str, result: Any):
        event = self.invokation_events.pop(invoke_id, None)
        if event is None:
            raise RuntimeError(f"Invokation event {invoke_id} not found")
        self.invokation_results[invoke_id] = result
        event.set()

    def set_invokation_exception(self, invoke_id: str, error_msg: str):
        event = self.invokation_events.pop(invoke_id, None)
        if event is None:
            raise RuntimeError(f"Invokation event {invoke_id} not found")
        self.invokation_exceptions[invoke_id] = ServerInvokationException(error_msg)
        event.set()
