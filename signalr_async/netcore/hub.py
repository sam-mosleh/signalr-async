from typing import Any, Sequence

from signalr_async.hub import HubBase

from .messages import InvocationMessage


class SignalRCoreHub(HubBase[InvocationMessage]):
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
