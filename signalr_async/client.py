import asyncio
import logging
from typing import Optional

from .connection import Connection
from .hub_proxy import HubProxy
from .invoke import InvokeManager


class SignalRClient:
    def __init__(
        self, url: str, extra_params: dict = {}, logger: Optional[logging.Logger] = None
    ):
        self._hubs = {}
        self._connection = Connection(url, extra_params=extra_params, logger=logger)
        self.logger = logger or logging.getLogger(__name__)
        self._producer_queue = asyncio.Queue()
        self._invoke_manager = InvokeManager(self._producer_queue)

    async def __aenter__(self):
        self._connection.hub_names = list(self._hubs.keys())
        await self._connection.start()
        self._consumer_task = asyncio.create_task(self._consumer())
        self._producer_task = asyncio.create_task(self._producer())

    async def __aexit__(self, exc_type, exc, tb):
        await self._connection.close()

    async def _consumer(self):
        while True:
            message = await self._connection.queue.get()
            self.logger.debug(f"Client message: {message}")
            try:
                await self._process_message(message)
            except Exception as e:
                self.logger.exception(str(e))

    async def _producer(self):
        while True:
            message = await self._producer_queue.get()
            await self._connection.send(message)

    async def _process_message(self, message: dict):
        if "P" in message:
            # Progress update message
            raise RuntimeError(f"Progress update message: {message}")
        if "I" in message:
            # Invokation result message
            self._invoke_manager.set_invokation_result(message["I"], message["R"])
        else:
            # Invoke message
            hub_name = message["H"]
            method_name = message["M"]
            args = message["A"]
            hub: HubProxy = self._hubs.get(hub_name)
            if hub is None:
                raise RuntimeError(f"Hub [{hub_name}] not found")
            await hub.call(method_name, args)

    def register(self, hub: HubProxy):
        hub.set_invoke_manager(self._invoke_manager)
        self._hubs[hub.name] = hub
        return self
