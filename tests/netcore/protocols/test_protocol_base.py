from typing import Any, Union

from signalr_async.netcore.messages import HubMessage
from signalr_async.netcore.protocols import ProtocolBase


class DummyProtocol(ProtocolBase):
    seperator: str = chr(0xF0)

    @property
    def name(self) -> str:
        return "dummy"

    @property
    def version(self) -> int:
        return 2

    @property
    def is_binary(self) -> bool:
        return False

    def decode(self, raw_messages: Union[str, bytes]):
        pass

    def parse(self, raw_messages: Union[str, bytes]):
        pass

    def encode(self, output: Any):
        pass

    def write(self, message: HubMessage):
        pass


def test_transfer_format():
    d = DummyProtocol()
    assert d.transfer_format == "Text"

    class BinaryDummyProtocol(DummyProtocol):
        @property
        def is_binary(self) -> bool:
            return True

    b = BinaryDummyProtocol()
    assert b.transfer_format == "Binary"


def test_handshake_params():
    d = DummyProtocol()
    assert d.handshake_params == '{"protocol": "dummy", "version": 2}' + d.seperator
