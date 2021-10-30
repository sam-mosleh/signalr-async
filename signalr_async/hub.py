import asyncio
import logging
from abc import abstractmethod
from typing import Any, Awaitable, Callable, Dict, List, Optional, Union

from .invoke_manager import InvokeManagerBase


class HubBase:
    def __init__(self, name: Optional[str] = None):
        self.name: str = name or type(self).__name__
        self._invoke_manager: Optional[InvokeManagerBase] = None
        self._logger: Optional[logging.Logger] = None
        self._callbacks: Dict[str, Callable] = {}
        for name in dir(self):
            if name.startswith("on_"):
                event_name = name[len("on_") :]
                self.on(event_name, getattr(self, name))

    def on(
        self, name: str, callback: Optional[Callable] = None
    ) -> Union[Callable, Callable[[Callable], Callable]]:
        def set_callback_decorator(callback: Callable) -> Callable:
            self._callbacks[name] = callback
            return callback

        return set_callback_decorator(callback) if callback else set_callback_decorator

    def _set_invoke_manager(self, invoke_manager: InvokeManagerBase) -> "HubBase":
        self._invoke_manager = invoke_manager
        return self

    def _set_logger(self, logger: logging.Logger) -> "HubBase":
        self._logger = logger
        return self

    async def _call(self, method_name: str, args: List[Any]) -> None:
        callback = self._callbacks.get(method_name)
        if callback is not None:
            asyncio.create_task(self._async_callback(callback, args))
        elif self._logger is not None:
            self._logger.warning(
                f"Method {method_name} doesnt exist in hub {self.name}"
            )

    async def _async_callback(self, callback: Callable, args: List[Any]) -> Any:
        if asyncio.iscoroutinefunction(callback):
            return await callback(*args)
        else:
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(None, callback, *args)

    @abstractmethod
    async def invoke(self, method: str, *args: Any) -> Dict[str, Any]:
        """Invoke a method of server"""

    async def on_connect(self, connection_id: str) -> None:
        """Connect event"""

    async def on_disconnect(self) -> None:
        """Disconnect event"""
