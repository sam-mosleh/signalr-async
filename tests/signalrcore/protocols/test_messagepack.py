from signalr_async.signalrcore.protocols import MessagePackProtocol
from signalr_async.signalrcore.messages import PingMessage, CompletionMessage

ping = PingMessage()


def test_messagepack_protocol_handshake_params():
    p = MessagePackProtocol()
    assert p.is_binary is True
    assert p.handshake_params == '{"protocol": "messagepack", "version": 1}\x1e'


def test_messagepack_protocol_parse():
    p = MessagePackProtocol()
    # assert list(p.decode(encoded_handshake)) == [handshake_dict]
    # assert list(p.decode(2 * encoded_handshake)) == [handshake_dict, handshake_dict]
    assert list(p.parse(b"\x02\x91\x06")) == [ping]


def test_messagepack_protocol_write():
    p = MessagePackProtocol()
    assert list(p.parse(b"\x02\x91\x06")) == [ping]
    assert p.write(ping) == b"\x02\x91\x06"
