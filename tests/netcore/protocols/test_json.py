from signalr_async.netcore.messages import CompletionMessage, MessageTypes, PingMessage
from signalr_async.netcore.protocols import JsonProtocol

handshake_dict = {"protocol": "json", "version": 1}
encoded_handshake = '{"protocol": "json", "version": 1}\x1e'
ping = PingMessage()
encoded_ping = '{"type": 6}\x1e'
completion = CompletionMessage(invocation_id="1", headers={}, result=True, error=None)
encoded_completion = '{"type": 3, "invocation_id": "1", "result": true}\x1e'


def test_handshake_params():
    p = JsonProtocol()
    assert p.is_binary is False
    assert p.handshake_params == encoded_handshake


def test_parse():
    p = JsonProtocol()
    assert list(p.decode(encoded_handshake)) == [handshake_dict]
    assert list(p.decode(2 * encoded_handshake)) == [handshake_dict, handshake_dict]
    assert list(p.parse(encoded_ping)) == [ping]
    assert list(p.parse(encoded_completion)) == [completion]


def test_write():
    p = JsonProtocol()
    assert p.encode({"type": 6}) == encoded_ping
    assert p.write(ping) == encoded_ping


def test_sanitize_raw_message():
    p = JsonProtocol()
    assert p._sanitize_raw_message_dict({"type": 1}) == (
        MessageTypes.INVOCATION,
        {
            "headers": {},
            "stream_ids": [],
            "invocation_id": None,
        },
    )
    assert p._sanitize_raw_message_dict({"type": 7}) == (
        MessageTypes.CLOSE,
        {
            "error": None,
            "allow_reconnect": None,
        },
    )
