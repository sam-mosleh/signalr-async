from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import IntEnum
from typing import Any, Dict, Optional, Sequence, Type, Union

from signalr_async.messages import InvocationBase


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
        """Message type of SignalRCore messages"""


@dataclass
class HubInvocableMessageBase(InvocationBase):
    invocation_id: str
    headers: Dict[str, Any]


@dataclass
class InvocationMessage(HubMessageBase, InvocationBase):
    target: str
    arguments: Sequence[Any]
    headers: Dict[str, Any]
    stream_ids: Sequence[str]

    @property
    def message_type(self) -> MessageTypes:
        return MessageTypes.INVOCATION


@dataclass
class StreamItemMessage(HubMessageBase, HubInvocableMessageBase):
    item: Dict[str, Any]

    @property
    def message_type(self) -> MessageTypes:
        return MessageTypes.STREAM_ITEM


@dataclass
class CompletionMessage(HubMessageBase, HubInvocableMessageBase):
    error: Optional[str]
    result: Optional[Dict[str, Any]]

    @property
    def message_type(self) -> MessageTypes:
        return MessageTypes.COMPLETION


@dataclass
class StreamInvocationMessage(HubMessageBase, HubInvocableMessageBase):
    target: str
    arguments: Sequence[Any]
    stream_ids: Sequence[Any]

    @property
    def message_type(self) -> MessageTypes:
        return MessageTypes.STREAM_INVOCATION


@dataclass
class CancelInvocationMessage(HubMessageBase, HubInvocableMessageBase):
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
    error: Optional[str]
    allow_reconnect: Optional[bool]

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

HubInvocableMessage = Union[
    InvocationMessage,
    StreamItemMessage,
    CompletionMessage,
    StreamInvocationMessage,
    CancelInvocationMessage,
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
