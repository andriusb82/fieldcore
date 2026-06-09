from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class PollingSlot:
    device_id: str
    command: str
    payload: dict[str, Any]
    interval: float = 1.0
    enabled: bool = True
    priority: int = 0
    timeout: float = 1.0
    retries: int = 3
