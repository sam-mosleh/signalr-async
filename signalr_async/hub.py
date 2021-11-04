import asyncio
import logging
from abc import abstractmethod
from typing import (
    Any,
    Awaitable,
    Callable,
    Dict,
    Generic,
    Optional,
    Sequence,
    TypeVar,
    Union,
)

from typing_extensions import TypeGuard

from .invoke_manager import InvokeManager
from .messages import InvocationBase

SyncFunctionType = Callable[..., None]
AsyncFunctionType = Callable[..., Awaitable[None]]
CallbackType = Union[SyncFunctionType, AsyncFunctionType]
DecoratorType = Callable[[CallbackType], CallbackType]

I = TypeVar("I", bound=InvocationBase)


class HubBase(Generic[I]):
    def __init__(self, name: Optional[str] = None):
        self.name: str = name or type(self).__name__
        self._invoke_manager: Optional[InvokeManager[I]] = None
        self._logger: Optional[logging.Logger] = None
        self._callbacks: Dict[str, CallbackType] = {}
        for name in dir(self):
            if name.startswith("on_"):
                event_name = name[len("on_") :]
                self.on(event_name, getattr(self, name))

    def on(
        self, name: Optional[str] = None, callback: Optional[CallbackType] = None
    ) -> Union[CallbackType, DecoratorType]:
        def set_callback_decorator(callback: CallbackType) -> CallbackType:
            self._callbacks[name or callback.__name__] = callback
            return callback

        return set_callback_decorator(callback) if callback else set_callback_decorator

    def _set_invoke_manager(self, invoke_manager: InvokeManager[I]) -> "HubBase[I]":
        self._invoke_manager = invoke_manager
        return self

    def _set_logger(self, logger: logging.Logger) -> "HubBase[I]":
        self._logger = logger
        return self

    async def _call(self, method_name: str, args: Sequence[Any]) -> None:
        callback = self._callbacks.get(method_name)
        if callback is not None:
            asyncio.create_task(self._async_callback(callback, args))
        elif self._logger is not None:
            self._logger.warning(
                f"Method {method_name} doesnt exist in hub {self.name}"
            )

    def _is_coroutine_function(
        self, callback: CallbackType
    ) -> TypeGuard[AsyncFunctionType]:
        return asyncio.iscoroutinefunction(callback)

    async def _async_callback(self, callback: CallbackType, args: Sequence[Any]) -> Any:
        if self._is_coroutine_function(callback):
            return await callback(*args)
        else:
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(None, callback, *args)

    async def invoke(self, method: str, *args: Any) -> Any:
        if self._invoke_manager is None:
            raise RuntimeError(f"Hub {self.name} is not registered")
        invocation_id = self._invoke_manager.next_invocation_id()
        message = self._create_invocation_message(invocation_id, method, args)
        return await self._invoke_manager.invoke_and_wait_for_result(
            invocation_id, message
        )

    @abstractmethod
    def _create_invocation_message(
        self, invocation_id: str, method: str, args: Sequence[Any]
    ) -> I:
        """Create invocation message"""

    async def on_connect(self, connection_id: str) -> None:
        """Connect event"""

    async def on_disconnect(self) -> None:
        """Disconnect event"""
