from typing import Any, List, Optional

from signalr_async.invoke_manager import InvokeManagerBase
from .messages import HubInvocation


class SignalRInvokeManager(InvokeManagerBase):
    async def invoke(  # type: ignore
        self, hub: str, method: str, method_args: Optional[List[Any]] = None
    ) -> Any:
        invocation_id = self._create_invocation_id()
        message = HubInvocation(
            invocation_id=invocation_id,
            hub=hub,
            target=method,
            arguments=method_args or [],
        )
        return await self._invoke_and_wait_for_result(invocation_id, message)
