from signalr_async.signalrcore import SignalRCoreConnection


def test_connection():
    url = "http://localhost"
    hub_name = "hub"
    SignalRCoreConnection(url, hub_name)
