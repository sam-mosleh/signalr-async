import asyncio
import logging
from abc import abstractmethod
from typing import Any, Awaitable, Callable, Dict, List, Optional

from .invoke_manager import InvokeManagerBase


class HubBase:
    def __init__(self, name: Optional[str] = None):
        self.name: str = name or type(self).__name__
        self._invoke_manager: Optional[InvokeManagerBase] = None
        self._logger: Optional[logging.Logger] = None
        self._callbacks: Dict[str, Callable[..., Awaitable[None]]] = {}
        for name in dir(self):
            if name.startswith("on_"):
                event_name = name[len("on_") :]
                self._callbacks[event_name] = getattr(self, name)

    def _set_invoke_manager(self, invoke_manager: InvokeManagerBase) -> "HubBase":
        self._invoke_manager = invoke_manager
        return self

    def _set_logger(self, logger: logging.Logger) -> "HubBase":
        self._logger = logger
        return self

    async def _call(self, method_name: str, args: List[Any]) -> None:
        callback = self._callbacks.get(method_name)
        if callback is not None:
            asyncio.create_task(callback(*args))
        if self._logger is not None:
            self._logger.warning(
                f"Method {method_name} doesnt exist in hub {self.name}"
            )

    @abstractmethod
    async def invoke(self, method: str, *args: Any) -> Dict[str, Any]:
        pass

    async def on_connect(self, connection_id: str) -> None:
        pass

    async def on_disconnect(self) -> None:
        pass
