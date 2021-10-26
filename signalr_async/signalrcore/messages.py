from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any, Dict, List, Optional, Type, Union


class MessageTypes(IntEnum):
    INVOCATION = 1
    STREAM_ITEM = 2
    COMPLETION = 3
    STREAM_INVOCATION = 4
    CANCEL_INVOCATION = 5
    PING = 6
    CLOSE = 7


class HubMessageBase(ABC):
    @property
    @abstractmethod
    def message_type(self) -> MessageTypes:
        pass


@dataclass
class InvocationMessage(HubMessageBase):
    target: str
    arguments: List[Any]
    headers: Optional[Dict[str, Any]] = None
    invocation_id: Optional[str] = None
    stream_ids: List[str] = field(default_factory=list)

    @property
    def message_type(self) -> MessageTypes:
        return MessageTypes.INVOCATION


@dataclass
class StreamItemMessage(HubMessageBase):
    invocation_id: str
    item: Dict[str, Any]
    headers: Optional[Dict[str, Any]] = None

    @property
    def message_type(self) -> MessageTypes:
        return MessageTypes.STREAM_ITEM


@dataclass
class CompletionMessage(HubMessageBase):
    invocation_id: str
    headers: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    result: Optional[Dict[str, Any]] = None

    @property
    def message_type(self) -> MessageTypes:
        return MessageTypes.COMPLETION


@dataclass
class StreamInvocationMessage(HubMessageBase):
    invocation_id: str
    target: str
    arguments: List[Any]
    stream_ids: List[Any]
    headers: Optional[Dict[str, Any]] = None

    @property
    def message_type(self) -> MessageTypes:
        return MessageTypes.STREAM_INVOCATION


@dataclass
class CancelInvocationMessage(HubMessageBase):
    invocation_id: str
    headers: Optional[Dict[str, Any]] = None

    @property
    def message_type(self) -> MessageTypes:
        return MessageTypes.CANCEL_INVOCATION


@dataclass
class PingMessage(HubMessageBase):
    @property
    def message_type(self) -> MessageTypes:
        return MessageTypes.PING


@dataclass
class CloseMessage(HubMessageBase):
    error: Optional[str] = None
    allow_reconnect: Optional[bool] = None

    @property
    def message_type(self) -> MessageTypes:
        return MessageTypes.CLOSE


HubMessage = Union[
    InvocationMessage,
    StreamItemMessage,
    CompletionMessage,
    StreamInvocationMessage,
    CancelInvocationMessage,
    PingMessage,
    CloseMessage,
]

message_type_to_class: Dict[MessageTypes, Type[HubMessage]] = {
    MessageTypes.INVOCATION: InvocationMessage,
    MessageTypes.STREAM_ITEM: StreamItemMessage,
    MessageTypes.COMPLETION: CompletionMessage,
    MessageTypes.STREAM_INVOCATION: StreamInvocationMessage,
    MessageTypes.CANCEL_INVOCATION: CancelInvocationMessage,
    MessageTypes.PING: PingMessage,
    MessageTypes.CLOSE: CloseMessage,
}
