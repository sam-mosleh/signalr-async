from signalr_async.signalrcore.client import SignalRCoreClient
from signalr_async.signalrcore.hub import SignalRCoreHub
from pytest_mock import MockFixture


def test_get_message_id(mocker: MockFixture):
    url = "http://localhost"
    client = SignalRCoreClient(url, SignalRCoreHub())
    message = mocker.MagicMock()
    assert client._get_message_id(message) == message.invocation_id
