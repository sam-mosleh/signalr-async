import asyncio
from typing import Any, Dict, Sequence

from signalr_async.client import SignalRClientBase

from .connection import SignalRConnection
from .hub import SignalRHub

# from .invoke_manager import SignalRInvokeManager
from .messages import HubInvocation, HubMessage, HubResult


class SignalRClient(SignalRClientBase[Sequence[SignalRHub], HubMessage, HubInvocation]):
    def build_connection(
        self,
        base_url: str,
        connection_options: Dict[str, Any],
    ) -> SignalRConnection:
        # TODO: Fix in base
        self._hub_dict = {h.name: h for h in self._hub}
        return SignalRConnection(
            base_url=base_url,
            hub_names=[hub.name for hub in self._hub],
            extra_params=connection_options.get("extra_params"),
            extra_headers=connection_options.get("extra_headers"),
            logger=self.logger,
        )

    async def _connection_event(self) -> None:
        if self._connection.connection_id:
            for hub in self._hub:
                asyncio.create_task(hub.on_connect(self._connection.connection_id))

    async def _disconnection_event(self) -> None:
        for hub in self._hub:
            asyncio.create_task(hub.on_disconnect())

    async def _process_message(self, message: HubMessage) -> None:
        if isinstance(message, HubResult):
            if message.progress_update is not None:
                self.logger.error(
                    f"ProgressUpdate messages are not implemented: {message}"
                )
            elif message.error is not None:
                self._invoke_manager.set_invocation_exception(
                    message.invocation_id, message.error
                )
            else:
                self._invoke_manager.set_invocation_result(
                    message.invocation_id, message.result
                )
        elif isinstance(message, HubInvocation):
            if message.hub is not None:
                await self._hub_dict[message.hub]._call(
                    message.target, message.arguments
                )
