import json
from dataclasses import asdict
from typing import Any, Dict, Generator, Tuple

from signalr_async.netcore.messages import (
    HubMessage,
    MessageTypes,
    message_type_to_class,
)

from .base import ProtocolBase


class JsonProtocol(ProtocolBase[str]):
    aliases = {
        "invocationId": "invocation_id",
        "streamIds": "stream_ids",
        "allowReconnect": "allow_reconnect",
    }
    aliases_reversed = {v: k for k, v in aliases.items()}

    @property
    def name(self) -> str:
        return "json"

    @property
    def version(self) -> int:
        return 1

    @property
    def is_binary(self) -> bool:
        return False

    def decode(self, raw_messages: str) -> Generator[Dict[str, Any], None, None]:
        for msg in raw_messages.split(self.seperator):
            if msg:
                yield json.loads(msg)

    def _sanitize_raw_message_dict(
        self, message: Dict[str, Any]
    ) -> Tuple[MessageTypes, Dict[str, Any]]:
        message_type = message.pop("type")
        if (
            message_type not in (MessageTypes.PING, MessageTypes.CLOSE)
            and "headers" not in message
        ):
            message["headers"] = {}
        if message_type == MessageTypes.COMPLETION:
            message["result"] = message.get("result")
            message["error"] = message.get("error")
        if message_type == MessageTypes.CLOSE:
            message["error"] = message.get("error")
            message["allow_reconnect"] = message.get("allow_reconnect")
        result = {self.aliases.get(key, key): val for key, val in message.items()}
        return MessageTypes(message_type), result

    def parse(self, raw_messages: str) -> Generator[HubMessage, None, None]:
        for message in self.decode(raw_messages):
            message_type, sanitized = self._sanitize_raw_message_dict(message)
            yield message_type_to_class[message_type](**sanitized)  # type: ignore

    def encode(self, output: Dict[str, Any]) -> str:
        return json.dumps(output) + self.seperator

    def write(self, message: HubMessage) -> str:
        output = {
            self.aliases_reversed.get(key, key): val
            for key, val in asdict(message).items()
            if val is not None
        }
        output["type"] = message.message_type
        return self.encode(output)
