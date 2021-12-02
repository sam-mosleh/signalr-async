import asyncio
from typing import Any

import pytest
from pytest_mock import MockerFixture

from signalr_async.client import SignalRClientBase

pytestmark = pytest.mark.asyncio


class DummySignalRClient(SignalRClientBase[Any, Any]):
    def build_connection(self, base_url, connection_options):
        pass

    async def _connection_event(self):
        pass

    async def _disconnection_event(self):
        pass

    async def _process_message(self, message):
        pass

    async def _consumer(self):
        pass

    async def _producer(self):
        pass

    async def _keepalive_handler(self):
        pass

    async def _timeout_handler(self):
        pass


async def test_context_manager(mocker: MockerFixture):
    client = DummySignalRClient("", [])
    mock_start = mocker.patch.object(client, "start")
    mock_stop = mocker.patch.object(client, "stop")
    mock_start.assert_not_awaited()
    async with client as client_started:
        assert client == client_started
        mock_start.assert_awaited_once()
        mock_stop.assert_not_awaited()
    mock_stop.assert_awaited_once()


async def test_start_connection(mocker: MockerFixture):
    client = DummySignalRClient("", [])
    mock_connection_event = mocker.patch.object(client, "_connection_event")
    client._connection = mocker.AsyncMock()
    client._connection.start.side_effect = [True, False]
    assert await client._start_connection() is True
    mock_connection_event.assert_awaited_once()
    assert await client._start_connection() is False
    mock_connection_event.assert_awaited_once()


async def test_stop_connection(mocker: MockerFixture):
    client = DummySignalRClient("", [])
    mock_disconnection_event = mocker.patch.object(client, "_disconnection_event")
    client._connection = mocker.AsyncMock()
    client._connection.stop.side_effect = [True, False]
    assert await client._stop_connection() is True
    mock_disconnection_event.assert_awaited_once()
    assert await client._stop_connection() is False
    mock_disconnection_event.assert_awaited_once()


async def test_start(mocker: MockerFixture):
    client = DummySignalRClient("", [])
    mock_start_connection = mocker.patch.object(
        client, "_start_connection", return_value=True
    )
    assert len(client._all_tasks) == 0
    await client.start()
    assert len(client._all_tasks) == 4
    for t in client._all_tasks:
        assert t.done(), "Tasks should be started"
        assert t.cancelled() is False


async def test_stop(mocker: MockerFixture):
    client = DummySignalRClient("", [])
    mock_task = mocker.MagicMock()
    client._all_tasks = {mock_task}
    mocker.patch.object(client, "_stop_connection")
    asyncio.gather = mocker.AsyncMock()
    await client.stop()
    assert len(client._all_tasks) == 0
    mock_task.cancel.assert_called_once()
    asyncio.gather.assert_awaited_once_with(mock_task)
