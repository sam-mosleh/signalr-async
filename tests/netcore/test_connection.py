from signalr_async.netcore import Connection


def test_connection():
    url = "http://localhost"
    hub_name = "hub"
    Connection(url, hub_name)
