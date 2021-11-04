import time

import aiohttp
import pytest
import yarl
from pytest_mock import MockFixture

from signalr_async.netcore.connection import SignalRCoreConnection

pytestmark = pytest.mark.asyncio


def test_common_params(mocker: MockFixture):
    url = "http://localhost"
    hub_name = "hub"
    conn = SignalRCoreConnection(
        url, hub_name, extra_params={"random_key": "random_value"}
    )
    assert conn._common_params() == {"random_key": "random_value"}
    connection_token = mocker.MagicMock()
    conn.connection_token = connection_token
    assert conn._common_params() == {
        "random_key": "random_value",
        "id": connection_token,
    }


def test_connect_path(mocker: MockFixture):
    url = "localhost"
    hub_name = "hub"
    conn = SignalRCoreConnection(
        f"http://{url}", hub_name, extra_params={"random_key": "random_value"}
    )
    conn.connection_token = "myconnectiontoken"
    connect_path = (
        yarl.URL(f"ws://{url}")
        / hub_name
        % {
            "random_key": "random_value",
            "id": "myconnectiontoken",
        }
    )
    assert conn._generate_connect_path() == connect_path


def test_write_message(mocker: MockFixture):
    url = "http://localhost"
    hub_name = "hub"
    conn = SignalRCoreConnection(url, hub_name)
    conn.protocol = mocker.MagicMock()
    conn.protocol.write.return_value = mocker.MagicMock()
    message = mocker.MagicMock()
    assert conn._write_message(message) == (
        conn.protocol.write.return_value,
        conn.protocol.is_binary,
    )
    conn.protocol.write.assert_called_once_with(message)


async def test_initialization(mocker: MockFixture):
    url = "http://localhost"
    hub_name = "hub"
    conn = SignalRCoreConnection(url, hub_name)
    conn._websocket = mocker.AsyncMock()
    conn._websocket.receive.return_value = aiohttp.WSMessage(
        aiohttp.WSMsgType.TEXT,
        "{}\x1e",
        None,
    )
    await conn._initialize_connection()
    conn._websocket._writer.send.assert_awaited_once_with(
        '{"protocol": "json", "version": 1}\x1e', False, compress=None
    )
    assert conn.last_message_received_time > time.time() - 1
    assert conn.last_message_sent_time > time.time() - 1
