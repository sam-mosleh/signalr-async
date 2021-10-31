import json

from pytest_mock import MockFixture

from signalr_async.net.connection import SignalRConnection
from signalr_async.net.messages import HubResult


def test_common_params():
    url = "http://localhost"
    hub_names = ["a", "b"]
    conn = SignalRConnection(
        url, hub_names, extra_params={"random_key": "random_value"}
    )
    assert conn._common_params() == {
        "clientProtocol": "1.5",
        "connectionData": '[{"name": "a"}, {"name": "b"}]',
        "random_key": "random_value",
    }
    conn.transport = "mytransport"
    conn.connection_token = "mytoken"
    assert conn._common_params() == {
        "clientProtocol": "1.5",
        "connectionData": '[{"name": "a"}, {"name": "b"}]',
        "random_key": "random_value",
        "transport": "mytransport",
        "connectionToken": "mytoken",
    }


def test_receive_params():
    url = "http://localhost"
    hub_names = ["a", "b"]
    conn = SignalRConnection(
        url, hub_names, extra_params={"random_key": "random_value"}
    )
    assert conn._receive_params() == {
        "clientProtocol": "1.5",
        "connectionData": '[{"name": "a"}, {"name": "b"}]',
        "random_key": "random_value",
    }
    conn.message_id = "mymessageid"
    conn.groups_token = "mygroupstoken"
    assert conn._receive_params() == {
        "clientProtocol": "1.5",
        "connectionData": '[{"name": "a"}, {"name": "b"}]',
        "random_key": "random_value",
        "messageId": "mymessageid",
        "groupsToken": "mygroupstoken",
    }


def test_read_message(mocker: MockFixture):
    groups_token = "G"
    message_id = "M"
    url = "http://localhost"
    conn = SignalRConnection(url)
    assert conn.groups_token is None
    assert conn.message_id is None
    data = {"C": message_id, "G": groups_token, "M": []}
    assert conn._read_message(json.dumps(data)) == []
    data = {"R": "abc", "I": "0"}
    assert conn._read_message(json.dumps(data)) == [
        HubResult(invocation_id=data["I"], result=data["R"])
    ]
    assert conn.groups_token == groups_token
    assert conn.message_id == message_id


def test_write_message(mocker: MockFixture):
    url = "http://localhost"
    conn = SignalRConnection(url)
    message = mocker.MagicMock()
    message.to_raw_message.return_value = mocker.MagicMock()
    mock_json_dumps = mocker.patch("json.dumps", return_value=mocker.MagicMock())
    assert conn._write_message(message) == (mock_json_dumps.return_value, False)
    mock_json_dumps.assert_called_once_with(message.to_raw_message.return_value)
