import asyncio

import pytest
from pytest_mock import MockFixture

from signalr_async.net.client import SignalRClient

pytestmark = pytest.mark.asyncio


async def test_client_connection_event(mocker: MockFixture):
    url = "http://localhost:3000"
    hub_one = mocker.MagicMock()
    hub_one.name = "test1"
    hub_two = mocker.MagicMock()
    hub_two.name = "test2"
    asyncio_create_task = mocker.patch.object(asyncio, "create_task")
    client = SignalRClient(url, [hub_one, hub_two])
    await client._connection_event()
    asyncio_create_task.assert_not_called()
    client._connection.connection_id = "myconnectionid"
    await client._connection_event()
    hub_one.on_connect.assert_called_once_with("myconnectionid")
    asyncio_create_task.assert_has_calls(
        [
            mocker.call(hub_one.on_connect()),
            mocker.call(hub_two.on_connect()),
        ]
    )
