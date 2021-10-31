from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from pytest_mock import MockerFixture

from signalr_async.connection import ConnectionBase

pytestmark = pytest.mark.asyncio


class DummyConnection(ConnectionBase[Any, Any]):
    async def _negotiate(self):
        pass

    def _generate_connect_path(self):
        pass

    async def _initialize_connection(self):
        pass

    def _read_message(self, data):
        pass

    def _write_message(self, message):
        pass


@pytest.fixture()
def mock_client_session(mocker: MockerFixture):
    session = mocker.MagicMock()
    session.close.side_effect = mocker.AsyncMock()
    mock_obj = mocker.patch("aiohttp.ClientSession", return_value=session)
    return session


@pytest.fixture()
def mock_ws_connect(mocker: MockerFixture, mock_client_session: MagicMock):
    async_mock = mocker.AsyncMock(return_value=mocker.MagicMock())
    async_mock.return_value.close.side_effect = mocker.AsyncMock()
    mock_client_session.ws_connect.side_effect = async_mock
    return async_mock


async def test_start(
    mocker: MockerFixture, mock_client_session: MagicMock, mock_ws_connect: AsyncMock
):
    url = "http://localhost"
    conn = DummyConnection(url)
    mock_negotiate = mocker.patch.object(conn, "_negotiate", autospec=True)
    mock_connect_path = mocker.patch.object(
        conn, "_generate_connect_path", autospec=True
    )
    mock_initialize_connection = mocker.patch.object(
        conn, "_initialize_connection", autospec=True
    )
    assert conn._session is None
    assert conn._websocket is None
    await conn.start()
    assert conn._session == mock_client_session
    assert conn._websocket == mock_ws_connect.return_value
    mock_negotiate.assert_called_once()
    mock_connect_path.assert_called_once()
    mock_initialize_connection.assert_called_once()


async def test_stop_with_stopped_connection(
    mocker: MockerFixture, mock_client_session: MagicMock, mock_ws_connect: AsyncMock
):
    url = "http://localhost"
    conn = DummyConnection(url)
    mock_clear_connection_data = mocker.patch.object(
        conn, "_clear_connection_data", autospec=True
    )
    assert conn._session is None
    assert conn._websocket is None
    await conn.stop()
    mock_clear_connection_data.assert_not_called()


async def test_stop_with_started_connection(
    mocker: MockerFixture, mock_client_session: MagicMock, mock_ws_connect: AsyncMock
):
    url = "http://localhost"
    conn = DummyConnection(url)
    mock_clear_connection_data = mocker.patch.object(
        conn, "_clear_connection_data", autospec=True
    )
    assert conn._session is None
    assert conn._websocket is None
    await conn.start()
    await conn.stop()
    mock_clear_connection_data.assert_called_once()
    mock_ws_connect.return_value.close.assert_called_once()
    mock_client_session.close.assert_called_once()


async def test_receive(mocker: MockerFixture):
    url = "http://localhost"
    conn = DummyConnection(url)
    timeout = 20
    received_val = mocker.MagicMock()
    read_val = mocker.MagicMock()
    mock_receive_raw = mocker.patch.object(
        conn, "_receive_raw", autospec=True, return_value=received_val
    )
    mock_read_message = mocker.patch.object(
        conn, "_read_message", autospec=True, return_value=read_val
    )
    assert await conn.receive(timeout=timeout) == read_val
    mock_receive_raw.assert_called_once_with(timeout=timeout)
    mock_read_message.assert_called_once_with(data=received_val)


async def test_send(mocker: MockerFixture):
    url = "http://localhost"
    conn = DummyConnection(url)
    message = mocker.MagicMock()
    sent_val = mocker.MagicMock()
    written_val = (mocker.MagicMock(), mocker.MagicMock())
    mock_send_raw = mocker.patch.object(
        conn, "_send_raw", autospec=True, return_value=sent_val
    )
    mock_write_message = mocker.patch.object(
        conn, "_write_message", autospec=True, return_value=written_val
    )
    assert await conn.send(message) == sent_val
    mock_send_raw.assert_called_once_with(*written_val)
    mock_write_message.assert_called_once_with(message=message)
