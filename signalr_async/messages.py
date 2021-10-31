from dataclasses import dataclass
from typing import Optional


@dataclass
class InvocationBase:
    invocation_id: Optional[str]
