from signalr_async.netcore.messages import CompletionMessage, PingMessage
from signalr_async.netcore.protocols import JsonProtocol

handshake_dict = {"protocol": "json", "version": 1}
encoded_handshake = '{"protocol": "json", "version": 1}\x1e'
ping = PingMessage()
encoded_ping = '{"type": 6}\x1e'
completion = CompletionMessage(invocation_id="1", headers={}, result=True, error=None)
encoded_completion = '{"type": 3, "invocation_id": "1", "result": true}\x1e'


def test_json_protocol_handshake_params():
    p = JsonProtocol()
    assert p.is_binary is False
    assert p.handshake_params == encoded_handshake


def test_json_protocol_parse():
    p = JsonProtocol()
    assert list(p.decode(encoded_handshake)) == [handshake_dict]
    assert list(p.decode(2 * encoded_handshake)) == [handshake_dict, handshake_dict]
    assert list(p.parse(encoded_ping)) == [ping]
    assert list(p.parse(encoded_completion)) == [completion]


def test_json_protocol_write():
    p = JsonProtocol()
    assert p.encode({"type": 6}) == encoded_ping
    assert p.write(ping) == encoded_ping
