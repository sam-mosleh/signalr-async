from typing import Any, List, Optional

from signalr_async.invoke_manager import InvokeManagerBase


class SignalRInvokeManager(InvokeManagerBase):
    async def invoke(  # type: ignore
        self, hub_name: str, method: str, method_args: Optional[List[Any]] = None
    ) -> Any:
        invokation_id = self._create_invokation_id()
        message = {"I": invokation_id, "H": hub_name, "M": method, "A": method_args}
        return await self._invoke_and_wait_for_result(invokation_id, message)
