import json
from typing import Any, Dict

from signalr_async.core.messages import (
    CloseMessage,
    CompletionMessage,
    HubMessageBase,
    InvocationMessage,
    MessageTypes,
    PingMessage,
    StreamItemMessage,
)

from .base import ProtocolBase


class JsonProtocol(ProtocolBase):
    aliases = {
        "type_": "type",
        "invocation_id": "invocationId",
        "stream_ids": "streamIds",
    }

    @property
    def name(self) -> str:
        return "json"

    @property
    def version(self) -> int:
        return 1

    @property
    def transfer_format(self) -> str:
        return "Text"

    @property
    def is_binary(self) -> bool:
        return False

    def decode(self, raw_messages: str):
        return [json.loads(msg) for msg in raw_messages.split(self.seperator) if msg]

    def parse(self, raw_messages: str):
        for message in self.decode(raw_messages):
            message_type = message["type"]
            if message_type == MessageTypes.INVOCATION:
                yield InvocationMessage(
                    headers=message.get("headers"),
                    invocation_id=message.get("invocationId"),
                    target=message["target"],
                    arguments=message["arguments"],
                    stream_ids=message.get("streamIds"),
                )
            elif message_type == MessageTypes.STREAM_ITEM:
                yield StreamItemMessage(
                    headers=message.get("headers"),
                    invocation_id=message["invocationId"],
                    item=message["item"],
                )
            elif message_type == MessageTypes.COMPLETION:
                yield CompletionMessage(
                    headers=message.get("headers"),
                    invocation_id=message["invocationId"],
                    error=message.get("error"),
                    result=message.get("result"),
                )
            elif message_type == MessageTypes.PING:
                yield PingMessage()
            elif message_type == MessageTypes.CLOSE:
                yield CloseMessage(
                    error=message.get("error"),
                    allow_reconnect=message.get("allowReconnect"),
                )
            else:
                raise Exception("Unknown message type")

    def encode(self, output: Dict[str, Any]):
        return json.dumps(output) + self.seperator

    def write(self, message: HubMessageBase):
        output = {
            self.aliases.get(key, key): val
            for key, val in message.__dict__.items()
            if val is not None
        }
        return self.encode(output)
