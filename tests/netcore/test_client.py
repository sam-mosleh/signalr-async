import asyncio

import pytest
from pytest_mock import MockFixture

from signalr_async.netcore.client import SignalRCoreClient

pytestmark = pytest.mark.asyncio


async def test_client_connection_event(mocker: MockFixture):
    url = "http://localhost:3000"
    hub = mocker.MagicMock()
    hub.name = "test1"
    asyncio_create_task = mocker.patch.object(asyncio, "create_task")
    client = SignalRCoreClient(url, hub)
    await client._connection_event()
    asyncio_create_task.assert_not_called()
    client._connection.connection_id = "myconnectionid"
    await client._connection_event()
    hub.on_connect.assert_called_once_with("myconnectionid")
    asyncio_create_task.assert_called_once_with(hub.on_connect())
