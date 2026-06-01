from __future__ import annotations

import multiprocessing
import threading
from typing import Type

from app.core.events import Event
from app.core.module import BaseModule


class ModuleManager:
    def __init__(self, context: "AppContext") -> None:
        self.context = context
        self.modules: dict[str, BaseModule] = {}
        self.threads: dict[str, threading.Thread] = {}
        self.processes: dict[str, multiprocessing.Process] = {}

    def create_modules(self, module_classes: list[Type[BaseModule]]) -> None:
        for module_class in module_classes:
            config = self.context.config.get_section(module_class.config_section)

            if not config.get("enabled", True):
                continue

            module = module_class(config=config, context=self.context)
            self.modules[module.name] = module
            module.register_event_handlers()

    def start_all(self) -> None:
        for module in self.modules.values():
            runner = module.config.get("runner", module.runner)

            if runner == "thread":
                thread = threading.Thread(
                    target=module.start,
                    name=module.name,
                    daemon=True,
                )
                self.threads[module.name] = thread
                thread.start()

            elif runner == "process":
                process = multiprocessing.Process(
                    target=module.start,
                    name=module.name,
                    daemon=True,
                )
                self.processes[module.name] = process
                process.start()

            else:
                module.start()

    def stop_all(self) -> None:
        for module in self.modules.values():
            module.stop()

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def register_event_handlers(self) -> None:
        self.context.event_bus.subscribe("config.changed", self.on_config_changed)

    def on_config_changed(self, event: Event) -> None:
        section = event.payload["section"]

        for module in self.modules.values():
            if module.config_section != section:
                continue

            old_config = event.payload["old_config"]
            new_config = event.payload["new_config"]

            if module.can_apply_config_live(old_config, new_config):
                module.apply_config(new_config)
            else:
                self.context.event_bus.publish(Event(
                    name="module.restart_required",
                    payload={
                        "module": module.name,
                        "section": section,
                    },
                ))