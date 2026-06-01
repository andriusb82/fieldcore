from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseModule(ABC):
    name: str = "base"
    config_section: str = "base"
    runner: str = "thread"  # thread, process, inline

    @classmethod
    def default_config(cls) -> dict[str, Any]:
        return {
            "enabled": True,
            "runner": cls.runner,
        }

    def __init__(self, config: dict[str, Any], context: "AppContext") -> None:
        self.config = config
        self.context = context
        self.running = False

    @abstractmethod
    def start(self) -> None:
        self.running = True

    @abstractmethod
    def stop(self) -> None:
        self.running = False

    def health(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "running": self.running,
        }

    def can_apply_config_live(
        self,
        old_config: dict[str, Any],
        new_config: dict[str, Any],
    ) -> bool:
        return True

    def apply_config(self, new_config: dict[str, Any]) -> None:
        self.config = new_config

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def register_event_handlers(self) -> None:
        pass