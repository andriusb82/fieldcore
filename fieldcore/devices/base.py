from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseTransport(ABC):
    @abstractmethod
    def connect(self) -> None:
        pass

    @abstractmethod
    def close(self) -> None:
        pass


class BaseDeviceDriver(ABC):
    @abstractmethod
    def read_status(self, device_id: str) -> dict[str, Any]:
        pass

    def read_measurements(self, device_id: str) -> dict[str, Any]:
        return {}

    def send_command(self, device_id: str, command: dict[str, Any]) -> dict[str, Any]:
        return {"ok": False, "error": "Command not implemented"}

    def capture_image(self, device_id: str) -> dict[str, Any]:
        return {"ok": False, "error": "Image capture not supported"}

    def get_capabilities(self) -> dict[str, Any]:
        return {
            "status": True,
            "measurements": False,
            "commands": False,
            "images": False,
        }