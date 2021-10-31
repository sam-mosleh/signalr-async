from typing import Any, Generator, Sequence, Tuple

import msgpack

from signalr_async.exceptions import InvalidMessage
from signalr_async.netcore.messages import (
    CancelInvocationMessage,
    CloseMessage,
    CompletionMessage,
    HubMessage,
    InvocationMessage,
    MessageTypes,
    PingMessage,
    StreamInvocationMessage,
    StreamItemMessage,
)

from .base import ProtocolBase


class MessagePackProtocol(ProtocolBase[bytes]):
    max_length_prefix_size: int = 5

    _error_result = 1
    _void_result = 2
    _non_void_result = 3

    @property
    def name(self) -> str:
        return "messagepack"

    @property
    def version(self) -> int:
        return 1

    @property
    def is_binary(self) -> bool:
        return True

    def _get_size(self, message: bytes, offset: int) -> Tuple[int, int]:
        total_readable_bytes = len(message) - offset
        num_bytes = 0
        size = 0
        while True:
            read_byte = message[offset + num_bytes]
            size = size | ((read_byte & 0x7F) << 7 * num_bytes)
            num_bytes += 1
            if num_bytes == self.max_length_prefix_size:
                if read_byte > 3:
                    raise InvalidMessage("Messages bigger than 2GB are not supported.")
                else:
                    return num_bytes, size
            elif (read_byte & 0x80) == 0:
                return num_bytes, size
            elif num_bytes >= total_readable_bytes:
                raise InvalidMessage("Cant read message size.")

    def decode(self, raw_messages: bytes) -> Generator[Sequence[Any], None, None]:
        offset = 0
        while offset < len(raw_messages):
            num_bytes, size = self._get_size(raw_messages, offset)
            if offset + num_bytes + size > len(raw_messages):
                raise InvalidMessage("Incomplete message.")
            yield msgpack.unpackb(
                raw_messages[offset + num_bytes : offset + num_bytes + size]
            )
            offset += num_bytes + size

    def parse(self, raw_messages: bytes) -> Generator[HubMessage, None, None]:
        for message in self.decode(raw_messages):
            message_type = message[0]
            if message_type == MessageTypes.INVOCATION:
                yield InvocationMessage(
                    headers=message[1],
                    invocation_id=message[2],
                    target=message[3],
                    arguments=message[4],
                    stream_ids=message[5],
                )
            elif message_type == MessageTypes.STREAM_ITEM:
                yield StreamItemMessage(
                    headers=message[1], invocation_id=message[2], item=message[3]
                )
            elif message_type == MessageTypes.COMPLETION:
                result_kind = message[3]
                yield CompletionMessage(
                    headers=message[1],
                    invocation_id=message[2],
                    error=message[4] if result_kind == self._error_result else None,
                    result=message[4] if result_kind == self._non_void_result else None,
                )
            elif message_type == MessageTypes.PING:
                yield PingMessage()
            elif message_type == MessageTypes.CLOSE:
                yield CloseMessage(
                    error=message[1],
                    allow_reconnect=message[2] if len(message) >= 3 else None,
                )
            else:
                raise RuntimeError("Unknown message")

    def encode(self, output: Sequence[Any]) -> bytes:
        encoded_output = msgpack.packb(output)
        size = len(encoded_output)
        length_prefix = b""
        while size > 0:
            size_part = size & 0x7F
            size >>= 7
            if size > 0:
                size_part |= 0x80
            length_prefix += size_part.to_bytes(1, "big")
        return length_prefix + encoded_output

    def write(self, message: HubMessage) -> bytes:
        output: Sequence[Any]
        if isinstance(message, InvocationMessage):
            output = [
                message.message_type,
                message.headers,
                message.invocation_id,
                message.target,
                message.arguments,
                message.stream_ids,
            ]
        elif isinstance(message, StreamInvocationMessage):
            output = [
                message.message_type,
                message.headers,
                message.invocation_id,
                message.target,
                message.arguments,
                message.stream_ids,
            ]
        elif isinstance(message, StreamItemMessage):
            output = [
                message.message_type,
                message.headers,
                message.invocation_id,
                message.item,
            ]
        elif isinstance(message, CompletionMessage):
            result_kind = (
                self._error_result
                if message.error
                else (self._non_void_result if message.result else self._void_result)
            )
            output = [
                message.message_type,
                message.headers,
                message.invocation_id,
                result_kind,
            ]
            output.append(result_kind)
            if result_kind != self._void_result:
                output.append(message.error or message.result)
        elif isinstance(message, PingMessage):
            output = [message.message_type]
        elif isinstance(message, CancelInvocationMessage):
            output = [
                message.message_type,
                message.headers,
                message.invocation_id,
            ]
        else:
            raise RuntimeError("Unknown message type")
        return self.encode(output)
