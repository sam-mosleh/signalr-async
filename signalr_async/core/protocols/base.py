import json
from abc import ABC, abstractmethod
from typing import Any, Union

from signalr_async.core.messages import HubMessageBase

StrBytes = Union[str, bytes]


class ProtocolBase(ABC):
    seperator: str = chr(0x1E)

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    @abstractmethod
    def version(self) -> int:
        pass

    @property
    @abstractmethod
    def transfer_format(self) -> str:
        pass

    @property
    @abstractmethod
    def is_binary(self) -> bool:
        pass

    @property
    def handshake_params(self) -> str:
        return (
            json.dumps({"protocol": self.name, "version": self.version})
            + self.seperator
        )

    @abstractmethod
    def decode(self, raw_messages: StrBytes):
        pass

    @abstractmethod
    def parse(self, raw_messages: StrBytes):
        pass

    @abstractmethod
    def encode(self, output: Any):
        pass

    @abstractmethod
    def write(self, message: HubMessageBase):
        pass
