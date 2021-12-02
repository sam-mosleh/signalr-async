import asyncio
import logging
from typing import Any, Dict, Optional

from signalr_async.client import SignalRClientBase

from .connection import SignalRCoreConnection
from .hub import SignalRCoreHub
from .messages import (
    CancelInvocationMessage,
    CloseMessage,
    CompletionMessage,
    HubInvocableMessage,
    HubMessage,
    InvocationMessage,
    PingMessage,
    StreamInvocationMessage,
    StreamItemMessage,
)


class SignalRCoreClient(SignalRClientBase[HubMessage, HubInvocableMessage]):
    def __init__(
        self,
        base_url: str,
        hub: SignalRCoreHub,
        timeout: float = 30,
        keepalive_interval: float = 15,
        reconnect_policy: bool = True,
        logger: Optional[logging.Logger] = None,
        connection_options: Optional[Dict[str, Any]] = None,
    ):
        self._hub = hub
        super().__init__(
            base_url,
            timeout,
            keepalive_interval,
            reconnect_policy,
            logger,
            connection_options,
        )
        self._hub._set_invoke_manager(self._invoke_manager)._set_logger(self.logger)

    def build_connection(
        self,
        base_url: str,
        connection_options: Dict[str, Any],
    ) -> SignalRCoreConnection:
        return SignalRCoreConnection(
            base_url=base_url,
            hub_name=self._hub.name,
            protocol=connection_options.get("protocol"),
            extra_params=connection_options.get("extra_params"),
            extra_headers=connection_options.get("extra_headers"),
            logger=self.logger,
        )

    async def _connection_event(self) -> None:
        if self._connection.connection_id:
            asyncio.create_task(self._hub.on_connect(self._connection.connection_id))

    async def _disconnection_event(self) -> None:
        asyncio.create_task(self._hub.on_disconnect())

    async def _process_message(self, message: HubMessage) -> None:
        if isinstance(message, InvocationMessage):
            await self._hub._call(message.target, message.arguments)
        elif isinstance(message, StreamItemMessage):
            self._invoke_manager.add_invocation_result(
                message.invocation_id, message.item
            )
        elif isinstance(message, CompletionMessage):
            if message.error:
                self._invoke_manager.set_invocation_exception(
                    message.invocation_id, message.error
                )
            else:
                self._invoke_manager.set_invocation_result(
                    message.invocation_id, message.result
                )
        elif isinstance(message, StreamInvocationMessage):
            self.logger.debug(f"Stream callback {message}")
        elif isinstance(message, CancelInvocationMessage):
            self.logger.debug(f"Cancel {message}")
        elif isinstance(message, PingMessage):
            self.logger.debug("[PING]")
        elif isinstance(message, CloseMessage):
            if message.error:
                self.logger.error(f"Server closed with reason: {message.error}")
            if message.allow_reconnect:
                await self._stop_connection()
            else:
                await asyncio.shield(self.stop())
        else:
            raise RuntimeError("Unknown message type")
