from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class Transaction:
    command: str
    payload: dict[str, Any]
    timeout: float = 1.0
    retries: int = 3
    priority: int = 0
