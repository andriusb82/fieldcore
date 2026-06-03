import json
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from threading import RLock
from typing import Any, Callable


@dataclass(slots=True)
class ConfigChangeEvent:
    section: str
    old_value: Any
    new_value: Any


class ConfigManager:
    def __init__(
        self,
        config_path: str | Path,
        default_config: dict[str, Any] | None = None,
        auto_create: bool = True,
    ) -> None:
        self._config_path = Path(config_path)
        self._default_config = deepcopy(default_config or {})
        self._config: dict[str, Any] = {}
        self._subscribers: dict[str, list[Callable[[ConfigChangeEvent], None]]] = {}
        self._lock = RLock()

        if auto_create and not self._config_path.exists():
            self._config = deepcopy(self._default_config)
            self.save()

        self.load()

    def load(self) -> dict[str, Any]:
        with self._lock:
            if not self._config_path.exists():
                self._config = deepcopy(self._default_config)
                return deepcopy(self._config)

            with open(self._config_path, "r", encoding="utf-8") as file:
                self._config = json.load(file)

            self._merge_missing_defaults(self._config, self._default_config)

            return deepcopy(self._config)

    def save(self) -> None:
        with self._lock:
            self._config_path.parent.mkdir(parents=True, exist_ok=True)

            with open(self._config_path, "w", encoding="utf-8") as file:
                json.dump(self._config, file, indent=4, ensure_ascii=False)

    def get_all(self) -> dict[str, Any]:
        with self._lock:
            return deepcopy(self._config)

    def get_section(self, section: str, default: Any = None) -> Any:
        with self._lock:
            return deepcopy(self._config.get(section, default))

    def update_section(self, section: str, value: Any, save: bool = True) -> None:
        with self._lock:
            old_value = deepcopy(self._config.get(section))
            self._config[section] = deepcopy(value)

            if save:
                self.save()

        self._notify_subscribers(
            ConfigChangeEvent(
                section=section,
                old_value=old_value,
                new_value=deepcopy(value),
            )
        )

    def update_value(self, section: str, key: str, value: Any, save: bool = True) -> None:
        with self._lock:
            section_data = self._config.setdefault(section, {})

            if not isinstance(section_data, dict):
                raise TypeError(f"Config section '{section}' is not a dictionary")

            old_section = deepcopy(section_data)
            section_data[key] = value

            if save:
                self.save()

        self._notify_subscribers(
            ConfigChangeEvent(
                section=section,
                old_value=old_section,
                new_value=deepcopy(section_data),
            )
        )

    def subscribe(
        self,
        section: str,
        callback: Callable[[ConfigChangeEvent], None],
    ) -> None:
        with self._lock:
            self._subscribers.setdefault(section, []).append(callback)

    def unsubscribe(
        self,
        section: str,
        callback: Callable[[ConfigChangeEvent], None],
    ) -> None:
        with self._lock:
            callbacks = self._subscribers.get(section, [])

            if callback in callbacks:
                callbacks.remove(callback)

    def reload(self) -> None:
        old_config = self.get_all()
        new_config = self.load()

        for section, new_value in new_config.items():
            old_value = old_config.get(section)

            if old_value != new_value:
                self._notify_subscribers(
                    ConfigChangeEvent(
                        section=section,
                        old_value=old_value,
                        new_value=deepcopy(new_value),
                    )
                )

    def _notify_subscribers(self, event: ConfigChangeEvent) -> None:
        callbacks = self._subscribers.get(event.section, [])

        for callback in callbacks:
            callback(event)

    @staticmethod
    def _merge_missing_defaults(
        target: dict[str, Any],
        defaults: dict[str, Any],
    ) -> None:
        for key, value in defaults.items():
            if key not in target:
                target[key] = deepcopy(value)
                continue

            if isinstance(value, dict) and isinstance(target[key], dict):
                ConfigManager._merge_missing_defaults(target[key], value)
