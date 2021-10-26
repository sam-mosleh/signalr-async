import json
from abc import ABC, abstractmethod
from typing import Any, Generator, Generic, TypeVar, Union
from signalr_async.signalrcore.messages import HubMessage

StrBytes = Union[str, bytes]

T = TypeVar("T")


class ProtocolBase(ABC, Generic[T]):
    seperator: str = chr(0x1E)

    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the protocol"""

    @property
    @abstractmethod
    def version(self) -> int:
        """Version of the protocol"""

    @property
    @abstractmethod
    def is_binary(self) -> bool:
        """Does the protocol use binary frames"""

    @property
    def transfer_format(self) -> str:
        return "Binary" if self.is_binary else "Text"

    @property
    def handshake_params(self) -> str:
        return (
            json.dumps({"protocol": self.name, "version": self.version})
            + self.seperator
        )

    @abstractmethod
    def decode(self, raw_messages: T) -> Generator[Any, None, None]:
        pass

    @abstractmethod
    def parse(self, raw_messages: T) -> Generator[HubMessage, None, None]:
        pass

    @abstractmethod
    def encode(self, output: Any) -> T:
        pass

    @abstractmethod
    def write(self, message: HubMessage) -> T:
        pass
