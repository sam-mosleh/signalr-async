import asyncio
from typing import Dict, Optional, Any

from signalr_async.client import SignalRClientBase

from .connection import SignalRCoreConnection
from .hub import SignalRCoreHub
from .invoke_manager import SignalRCoreInvokeManager
from .messages import (
    CancelInvocationMessage,
    CloseMessage,
    CompletionMessage,
    HubMessage,
    InvocationMessage,
    PingMessage,
    StreamInvocationMessage,
    StreamItemMessage,
)
from .protocols import ProtocolBase


class SignalRCoreClient(SignalRClientBase[SignalRCoreHub]):
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

    def build_invoke_manager(self) -> SignalRCoreInvokeManager:
        invoke_manager = SignalRCoreInvokeManager(self._producer_queue)
        self._hub._set_invoke_manager(invoke_manager)._set_logger(self.logger)
        return invoke_manager

    async def _connection_event(self) -> None:
        if self._connection.connection_id:
            asyncio.create_task(self._hub.on_connect(self._connection.connection_id))

    async def _disconnection_event(self) -> None:
        asyncio.create_task(self._hub.on_disconnect())

    def _get_message_id(self, message: InvocationMessage) -> str:
        return message.invocation_id  # type: ignore

    async def _process_message(self, message: HubMessage) -> None:
        if isinstance(message, InvocationMessage):
            self.logger.info(f"Callback {message}")
            await self._hub._call(message.target, message.arguments)
        elif isinstance(message, StreamItemMessage):
            self.logger.info(f"Stream {message}")
        elif isinstance(message, CompletionMessage):
            if message.error:
                self._invoke_manager.set_invokation_exception(
                    message.invocation_id, message.error
                )
            else:
                self._invoke_manager.set_invokation_result(
                    message.invocation_id, message.error
                )
        elif isinstance(message, StreamInvocationMessage):
            self.logger.info(f"Stream callback {message}")
        elif isinstance(message, CancelInvocationMessage):
            self.logger.info(f"Cancel {message}")
        elif isinstance(message, PingMessage):
            self.logger.info("[PING]")
        elif isinstance(message, CloseMessage):
            if message.error:
                self.logger.error(f"Server closed with reason: {message.error}")
            if self.reconnect_policy and message.allow_reconnect:
                await self._connection.stop()
            else:
                await asyncio.shield(self.stop())
        else:
            raise Exception("Unknown message type")