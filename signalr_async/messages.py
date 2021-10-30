from typing import Optional, List, Any
from dataclasses import dataclass


@dataclass
class InvocationBase:
    target: str
    arguments: List[Any]
    invocation_id: Optional[str] = None
