import asyncio
import logging
from typing import Any, Dict, Optional, Sequence

from signalr_async.client import SignalRClientBase

from .connection import SignalRConnection
from .hub import SignalRHub

# from .invoke_manager import SignalRInvokeManager
from .messages import HubInvocation, HubMessage, HubResult


class SignalRClient(SignalRClientBase[HubMessage, HubInvocation]):
    def __init__(
        self,
        base_url: str,
        hubs: Sequence[SignalRHub],
        timeout: float = 30,
        keepalive_interval: float = 15,
        reconnect_policy: bool = True,
        logger: Optional[logging.Logger] = None,
        connection_options: Optional[Dict[str, Any]] = None,
    ):
        self._hubs = hubs
        self._hub_dict = {h.name: h for h in self._hubs}
        super().__init__(
            base_url,
            timeout,
            keepalive_interval,
            reconnect_policy,
            logger,
            connection_options,
        )
        for h in self._hubs:
            h._set_invoke_manager(self._invoke_manager)._set_logger(self.logger)

    def build_connection(
        self,
        base_url: str,
        connection_options: Dict[str, Any],
    ) -> SignalRConnection:
        return SignalRConnection(
            base_url=base_url,
            hub_names=[hub.name for hub in self._hubs],
            extra_params=connection_options.get("extra_params"),
            extra_headers=connection_options.get("extra_headers"),
            logger=self.logger,
        )

    async def _connection_event(self) -> None:
        if self._connection.connection_id:
            for hub in self._hubs:
                asyncio.create_task(hub.on_connect(self._connection.connection_id))

    async def _disconnection_event(self) -> None:
        for hub in self._hubs:
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
