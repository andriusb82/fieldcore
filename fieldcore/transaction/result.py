from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class TransactionResult:
    ok: bool
    response: Any = None
    error: str | None = None
