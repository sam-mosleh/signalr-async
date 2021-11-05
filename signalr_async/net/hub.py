from typing import Any, Sequence

from signalr_async.hub import HubBase

from .messages import HubInvocation


class SignalRHub(HubBase[HubInvocation]):
    def _create_invocation_message(
        self, invocation_id: str, method: str, args: Sequence[Any]
    ) -> HubInvocation:
        return HubInvocation(
            invocation_id=invocation_id,
            hub=self.name,
            target=method,
            arguments=args or tuple(),
            state=None,
        )
