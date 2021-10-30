import asyncio
from typing import Any, Dict, List

from signalr_async.client import SignalRClientBase

from .connection import SignalRConnection
from .hub import SignalRHub
from .invoke_manager import SignalRInvokeManager
from .messages import HubInvocation, HubMessage, HubResult


class SignalRClient(SignalRClientBase[List[SignalRHub], HubInvocation, HubMessage]):
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

    def build_invoke_manager(self) -> SignalRInvokeManager:
        invoke_manager = SignalRInvokeManager(self._producer_queue)
        for hub in self._hub:
            hub._set_invoke_manager(invoke_manager)._set_logger(self.logger)
        return invoke_manager

    async def _connection_event(self) -> None:
        if self._connection.connection_id:
            for hub in self._hub:
                asyncio.create_task(hub.on_connect(self._connection.connection_id))

    async def _disconnection_event(self) -> None:
        for hub in self._hub:
            asyncio.create_task(hub.on_disconnect())

    async def _process_message(self, message: HubMessage) -> None:
        if isinstance(message, HubResult):
            if message.progress_update:
                self.logger.error(
                    f"ProgressUpdate messages are not implemented: {message}"
                )
            elif message.result:
                self._invoke_manager.set_invocation_result(
                    message.invocation_id, message.result
                )
            elif message.error:
                self._invoke_manager.set_invocation_exception(
                    message.invocation_id, message.error
                )
            else:
                self.logger.error(f"Bad HubResult: {message}")
        elif isinstance(message, HubInvocation):
            if message.hub:
                await self._hub_dict[message.hub]._call(
                    message.target, message.arguments
                )
