from signalr_async.hub import HubBase
from typing import Dict, Any


class SignalRCoreHub(HubBase):
    async def invoke(self, method: str, *args: Any) -> Dict[str, Any]:
        if self._invoke_manager is None:
            raise RuntimeError(f"Hub {self.name} is not registered")
        return await self._invoke_manager.invoke(method, args)
