from __future__ import annotations

import yaml
from pathlib import Path
from typing import Any, Type

from fieldcore.core.events import Event, LocalEventBus
from fieldcore.core.module import BaseModule


class ConfigManager:
    def __init__(
        self,
        config_path: str,
        module_classes: list[Type[BaseModule]],
        event_bus: LocalEventBus,
    ) -> None:
        self.config_path = Path(config_path)
        self.module_classes = module_classes
        self.event_bus = event_bus
        self.config: dict[str, Any] = {}

    def load_or_create(self) -> dict[str, Any]:
        defaults = self._collect_defaults()

        if self.config_path.exists():
            loaded = yaml.safe_load(self.config_path.read_text()) or {}
        else:
            loaded = {}

        self.config = self._merge_missing_defaults(loaded, defaults)
        self.save()
        return self.config

    def get_section(self, section: str) -> dict[str, Any]:
        return self.config.get(section, {})

    def update_section(self, section: str, new_values: dict[str, Any]) -> None:
        old_config = self.config.get(section, {}).copy()

        self.config.setdefault(section, {})
        self.config[section].update(new_values)

        self.save()

        self.event_bus.publish(Event(
            name="config.changed",
            payload={
                "section": section,
                "old_config": old_config,
                "new_config": self.config[section],
            },
        ))

    def save(self) -> None:
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text(
            yaml.safe_dump(self.config, sort_keys=False)
        )

    def _collect_defaults(self) -> dict[str, Any]:
        result: dict[str, Any] = {}

        for module_class in self.module_classes:
            result[module_class.config_section] = module_class.default_config()

        return result

    def _merge_missing_defaults(
        self,
        current: dict[str, Any],
        defaults: dict[str, Any],
    ) -> dict[str, Any]:
        for section, values in defaults.items():
            current.setdefault(section, {})

            for key, value in values.items():
                current[section].setdefault(key, value)

        return current