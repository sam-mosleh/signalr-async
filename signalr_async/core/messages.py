from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any, Dict, List, Optional, Union


class MessageTypes(IntEnum):
    INVOCATION = 1
    STREAM_ITEM = 2
    COMPLETION = 3
    STREAM_INVOCATION = 4
    CANCEL_INVOCATION = 5
    PING = 6
    CLOSE = 7


class HubMessageBase:
    type_: MessageTypes


@dataclass
class InvocationMessage(HubMessageBase):
    invocation_id: str
    target: str
    arguments: List[Any]
    headers: Optional[Dict[str, Any]] = None
    type_: MessageTypes = MessageTypes.INVOCATION
    stream_ids: List[str] = field(default_factory=list)


@dataclass
class StreamItemMessage(HubMessageBase):
    invocation_id: str
    item: Dict[str, Any]
    headers: Optional[Dict[str, Any]] = None
    type_: MessageTypes = MessageTypes.STREAM_ITEM


@dataclass
class CompletionMessage(HubMessageBase):
    invocation_id: str
    headers: Optional[Dict[str, Any]] = None
    type_: MessageTypes = MessageTypes.COMPLETION
    error: Optional[str] = None
    result: Optional[Dict[str, Any]] = None


@dataclass
class StreamInvocationMessage(HubMessageBase):
    invocation_id: str
    target: str
    arguments: list
    stream_ids: list
    headers: Optional[Dict[str, Any]] = None
    type_: MessageTypes = MessageTypes.STREAM_INVOCATION


@dataclass
class CancelInvocationMessage(HubMessageBase):
    invocation_id: str
    headers: Optional[Dict[str, Any]] = None
    type_: MessageTypes = MessageTypes.CANCEL_INVOCATION


@dataclass
class PingMessage(HubMessageBase):
    type_: MessageTypes = MessageTypes.PING


@dataclass
class CloseMessage(HubMessageBase):
    type_: MessageTypes = MessageTypes.CLOSE
    error: str = None
    allow_reconnect: bool = None


HubMessage = Union[
    InvocationMessage,
    StreamItemMessage,
    CompletionMessage,
    StreamInvocationMessage,
    CancelInvocationMessage,
    PingMessage,
    CloseMessage,
]
