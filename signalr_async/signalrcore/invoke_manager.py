from typing import Any, List, Optional

from signalr_async.invoke_manager import InvokeManagerBase

from .messages import InvocationMessage


class SignalRCoreInvokeManager(InvokeManagerBase):
    async def invoke(self, method: str, method_args: Optional[List[Any]] = None) -> Any:  # type: ignore
        invocation_id = self._create_invocation_id()
        message = InvocationMessage(
            invocation_id=invocation_id, target=method, arguments=method_args or []
        )
        return await self._invoke_and_wait_for_result(invocation_id, message)
