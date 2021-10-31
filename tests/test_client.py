from typing import Any

import pytest
from pytest_mock import MockerFixture

from signalr_async.client import SignalRClientBase

pytestmark = pytest.mark.asyncio


class DummySignalRClient(SignalRClientBase[Any, Any, Any]):
    def build_connection(self, base_url, connection_options):
        pass

    async def _connection_event(self):
        pass

    async def _disconnection_event(self):
        pass

    async def _process_message(self, message):
        pass


async def test_client_context_manager(mocker: MockerFixture):
    client = DummySignalRClient("", [])
    mock_start = mocker.patch.object(client, "start")
    mock_stop = mocker.patch.object(client, "stop")
    mock_start.assert_not_awaited()
    async with client as client_started:
        assert client == client_started
        mock_start.assert_awaited_once()
        mock_stop.assert_not_awaited()
    mock_stop.assert_awaited_once()
