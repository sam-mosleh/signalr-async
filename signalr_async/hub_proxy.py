import asyncio
import logging
from typing import Callable, List, Optional

from .invoke import InvokeManager


class HubProxy:
    def __init__(self, name: Optional[str] = None):
        self.name = name or type(self).__name__
        self._invoke_manager = None
        self._logger = None
        self._callbacks = {}
        for name in dir(self):
            if name.startswith("on_"):
                event_name = name[len("on_") :]
                self._callbacks[event_name] = getattr(self, name)

    def set_invoke_manager(self, invoke_manager: InvokeManager):
        self._invoke_manager = invoke_manager
        return self

    def set_logger(self, logger: logging.Logger):
        self._logger = logger
        return self

    async def invoke(self, method: str, *args):
        if self._invoke_manager is None:
            raise RuntimeError("Proxy is not registered")
        return await self._invoke_manager.invoke(
            hub_name=self.name, method=method, method_args=args
        )

    async def call(self, method_name: str, args: List[any]):
        callback = self._callbacks.get(method_name)
        if callback is not None:
            task = asyncio.create_task(callback(*args))
            await asyncio.sleep(0)
            return task
        self._logger.warning(f"Method {method_name} doesnt exist in hub {self.name}")

    def on(self, name: str):
        def add_to_callbacks_decorator(func: Callable):
            self._callbacks[name] = func
            return func

        return add_to_callbacks_decorator
