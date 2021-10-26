import json
from typing import Any, Dict, Generator

from signalr_async.signalrcore.messages import HubMessage, message_type_to_class

from .base import ProtocolBase


class JsonProtocol(ProtocolBase[str]):
    aliases = {
        "type": "message_type",
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

    def parse(self, raw_messages: str) -> Generator[HubMessage, None, None]:
        for message in self.decode(raw_messages):
            message_type = message.pop("type")
            yield message_type_to_class[message_type](  # type: ignore
                **{self.aliases.get(key, key): val for key, val in message.items()}
            )

    def encode(self, output: Dict[str, Any]) -> str:
        return json.dumps(output) + self.seperator

    def write(self, message: HubMessage) -> str:
        output = {
            self.aliases_reversed.get(key, key): val
            for key, val in message.__dict__.items()
            if val is not None
        }
        return self.encode(output)
