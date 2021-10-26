from signalr_async.signalr.client import SignalRClient
from pytest_mock import MockFixture


def test_get_message_id(mocker: MockFixture):
    url = "http://localhost"
    client = SignalRClient(url, [])
    message_id = mocker.MagicMock()
    assert client._get_message_id({"I": message_id}) == message_id
