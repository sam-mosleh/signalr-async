from dataclasses import dataclass
from typing import Any, List, Optional


@dataclass
class InvocationBase:
    target: str
    arguments: List[Any]
    invocation_id: Optional[str] = None
