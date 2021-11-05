from dataclasses import dataclass
from typing import Any, Dict, Optional, Sequence, Union

from signalr_async.messages import InvocationBase


@dataclass
class HubInvocation(InvocationBase):
    hub: str
    target: str
    arguments: Sequence[Any]
    state: Optional[Dict[str, Any]]

    @classmethod
    def from_raw_message(cls, raw_message: Dict[str, Any]) -> "HubInvocation":
        return cls(
            invocation_id=raw_message.get("I"),
            hub=raw_message["H"],
            target=raw_message["M"],
            arguments=raw_message["A"],
            state=raw_message.get("S"),
        )

    def to_raw_message(self) -> Dict[str, Any]:
        result = {
            "H": self.hub,
            "M": self.target,
            "A": self.arguments,
        }
        if self.invocation_id:
            result["I"] = self.invocation_id
        return result


@dataclass
class HubResult:
    invocation_id: str
    result: Optional[Any]
    error: Optional[str]
    error_data: Optional[Any]
    is_hub_exception: Optional[bool]
    progress_update: Optional[Any]
    state: Optional[Any]

    @classmethod
    def from_raw_message(cls, raw_message: Dict[str, Any]) -> "HubResult":
        return cls(
            invocation_id=raw_message["I"],
            result=raw_message.get("R"),
            error=raw_message.get("E"),
            error_data=raw_message.get("D"),
            is_hub_exception=raw_message.get("H"),
            progress_update=raw_message.get("P"),
            state=raw_message.get("S"),
        )


HubMessage = Union[HubInvocation, HubResult]
