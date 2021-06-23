import asyncio
import logging
from typing import Optional

from websockets.exceptions import ConnectionClosed, ConnectionClosedOK

from .connection import Connection
from .hub_proxy import HubProxy
from .invoke import InvokeManager


class SignalRClient:
    def __init__(
        self, url: str, extra_params: dict = {}, logger: Optional[logging.Logger] = None
    ):
        self._hubs = {}
        self._logger = logger or logging.getLogger(__name__)
        self._connection = Connection(
            url, extra_params=extra_params, logger=self._logger
        )
        self._producer_queue = asyncio.Queue()
        self._invoke_manager = InvokeManager(self._producer_queue)

    async def __aenter__(self):
        self._connection.hub_names = list(self._hubs.keys())
        await self._connection.start()
        self._consumer_task = asyncio.create_task(self._consumer())
        self._producer_task = asyncio.create_task(self._producer())
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if exc_type != asyncio.CancelledError:
            self._consumer_task.cancel()
            self._producer_task.cancel()
        await self._connection.close()

    async def _consumer(self):
        while True:
            try:
                message = await self._connection.receive()
            except ConnectionClosedOK:
                self._logger.info("Connection is closed. Consumer done.")
                return
            self._logger.debug(f"Client message: {message}")
            try:
                await self._process_message(message)
            except Exception as e:
                self._logger.exception(str(e))

    async def _producer(self):
        while True:
            message = await self._producer_queue.get()
            try:
                await self._connection.send(message)
            except ConnectionClosed:
                self._logger.error(
                    f"Message {message['I']} has not been sent because connection is closed"
                )
                # TODO: add another type of invokation exception to raise
                self._invoke_manager.set_invokation_exception(
                    message["I"], "Connection is closed"
                )

    async def _process_message(self, message: dict):
        if message:
            if "P" in message:
                # Progress update message
                raise RuntimeError(f"Progress update message: {message}")
            if "I" in message:
                if "R" in message:
                    # Invokation result message
                    self._invoke_manager.set_invokation_result(
                        message["I"], message["R"]
                    )
                elif "E" in message:
                    # Invokation exception
                    self._invoke_manager.set_invokation_exception(
                        message["I"], message["E"]
                    )
                else:
                    raise RuntimeError(f"Progress invoke message: {message}")
            else:
                # Invoke message
                for invoke_message in message["M"]:
                    hub_name = invoke_message["H"]
                    method_name = invoke_message["M"]
                    args = invoke_message["A"]
                    hub: HubProxy = self._hubs.get(hub_name)
                    if hub is None:
                        raise RuntimeError(f"Hub [{hub_name}] not found")
                    await hub.call(method_name, args)

    def register(self, hub: HubProxy):
        hub.set_invoke_manager(self._invoke_manager).set_logger(self._logger)
        self._hubs[hub.name] = hub
        return self

    async def wait(self):
        return await self._consumer_task
