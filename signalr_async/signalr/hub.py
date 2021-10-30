from typing import Any, Dict

from signalr_async.hub import HubBase


class SignalRHub(HubBase):
    async def invoke(self, method: str, *args: Any) -> Dict[str, Any]:
        if self._invoke_manager is None:
            raise RuntimeError(f"Hub {self.name} is not registered")
        return await self._invoke_manager.invoke(self.name, method, args)
