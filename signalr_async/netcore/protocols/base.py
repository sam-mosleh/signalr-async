import json
from abc import ABC, abstractmethod
from typing import Any, Generator, Generic, TypeVar

from signalr_async.netcore.messages import HubMessage

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
        """Generator which decodes messages from connection to python objects"""

    @abstractmethod
    def parse(self, raw_messages: T) -> Generator[HubMessage, None, None]:
        """Parse raw message from connection to HubMessge using decode method"""

    @abstractmethod
    def encode(self, output: Any) -> T:
        """Encode python objects to transferable format"""

    @abstractmethod
    def write(self, message: HubMessage) -> T:
        """Transform HubMessage to transferable format"""
