import pytest
from pytest_mock import MockerFixture

from signalr_async.exceptions import InvalidMessage
from signalr_async.signalrcore.messages import InvocationMessage, PingMessage
from signalr_async.signalrcore.protocols import MessagePackProtocol

ping = PingMessage()


def test_messagepack_protocol_handshake_params():
    p = MessagePackProtocol()
    assert p.is_binary is True
    assert p.handshake_params == '{"protocol": "messagepack", "version": 1}\x1e'


def test_messagepack_protocol_parse_raw_ping():
    p = MessagePackProtocol()
    assert list(p.parse(b"\x02\x91\x06")) == [ping]


def test_messagepack_protocol_write():
    p = MessagePackProtocol()
    assert list(p.parse(b"\x02\x91\x06")) == [ping]
    assert p.write(ping) == b"\x02\x91\x06"


def test_get_size():
    p = MessagePackProtocol()
    assert p._get_size(b"\x01", 0) == (1, 2 ** 0)
    assert p._get_size(b"\x81\x01", 0) == (2, 2 ** 7 + 2 ** 0)
    with pytest.raises(InvalidMessage):
        p._get_size(b"\x80", 0)


def test_get_big_message_size():
    p = MessagePackProtocol()
    assert p._get_size(b"\x80" * 4 + b"\x03", 0) == (5, 3 * 2 ** 28)
    with pytest.raises(InvalidMessage):
        p._get_size(b"\x80" * 4 + b"\x04", 0)  # 2 ** 30 bytes = 2GB


def test_decode_partial_message():
    p = MessagePackProtocol()
    with pytest.raises(InvalidMessage):
        list(p.decode(b"\x01"))


def test_messagepack_protocol_parse(mocker: MockerFixture):
    p = MessagePackProtocol()
    mock_decode = mocker.patch.object(p, "decode")
    messages = [
        [6],
        [
            1,
            mocker.MagicMock(),
            mocker.MagicMock(),
            mocker.MagicMock(),
            mocker.MagicMock(),
            mocker.MagicMock(),
        ],
    ]
    mock_decode.return_value = messages
    assert list(p.parse(None)) == [
        PingMessage(),
        InvocationMessage(
            headers=messages[1][1],
            invocation_id=messages[1][2],
            target=messages[1][3],
            arguments=messages[1][4],
            stream_ids=messages[1][5],
        ),
    ]
