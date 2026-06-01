from __future__ import annotations

from datetime import datetime
from threading import RLock
from typing import Any


class StateRegistry:
    def __init__(self) -> None:
        self._devices: dict[str, dict[str, Any]] = {}
        self._modules: dict[str, dict[str, Any]] = {}
        self._alarms: dict[str, dict[str, Any]] = {}
        self._lock = RLock()

    def update_device_state(self, device_id: str, state: dict[str, Any]) -> None:
        with self._lock:
            current = self._devices.get(device_id, {})
            current.update(state)
            current["updated_at"] = datetime.utcnow().isoformat()
            self._devices[device_id] = current

    def get_device_state(self, device_id: str) -> dict[str, Any] | None:
        with self._lock:
            return self._devices.get(device_id)

    def get_all_device_states(self) -> dict[str, dict[str, Any]]:
        with self._lock:
            return dict(self._devices)

    def update_alarm_state(self, alarm_id: str, state: dict[str, Any]) -> None:
        with self._lock:
            self._alarms[alarm_id] = state

    def get_alarm_states(self) -> dict[str, dict[str, Any]]:
        with self._lock:
            return dict(self._alarms)