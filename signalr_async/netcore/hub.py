from typing import Any, AsyncGenerator, Sequence

from signalr_async.hub import HubBase

from .messages import (
    CancelInvocationMessage,
    HubInvocableMessage,
    InvocationMessage,
    StreamInvocationMessage,
)


class SignalRCoreHub(HubBase[HubInvocableMessage]):
    def _create_invocation_message(
        self, invocation_id: str, method: str, args: Sequence[Any]
    ) -> InvocationMessage:
        return InvocationMessage(
            invocation_id=invocation_id,
            target=method,
            arguments=args or tuple(),
            headers={},
            stream_ids=tuple(),
        )

    async def stream(self, method: str, *args: Any) -> AsyncGenerator[Any, None]:
        if self._invoke_manager is None:
            raise RuntimeError(f"Hub {self.name} is not registered")
        invocation_id = self._invoke_manager.next_invocation_id()
        message = StreamInvocationMessage(
            invocation_id=invocation_id,
            target=method,
            arguments=args,
            headers={},
            stream_ids=tuple(),
        )
        async for result in self._invoke_manager.invoke_and_wait_for_stream(
            invocation_id, message
        ):
            try:
                yield result
            except GeneratorExit:
                if self._logger:
                    self._logger.debug(f"Closing stream {invocation_id} with {method=}")
                await self._invoke_manager.invoke(
                    CancelInvocationMessage(invocation_id=invocation_id, headers={})
                )
                break
