from __future__ import annotations

from typing import Any

from app.core.events import Event
from app.core.module import BaseModule


class ApiModule(BaseModule):
    name = "api"
    config_section = "api"
    runner = "thread"

    @classmethod
    def default_config(cls) -> dict[str, Any]:
        return {
            "enabled": True,
            "runner": "thread",
            "host": "0.0.0.0",
            "port": 8080,
        }

    def start(self) -> None:
        self.running = True
        # Later: start FastAPI/Flask server here.

    def stop(self) -> None:
        self.running = False

    def request_device_refresh(self, device_id: str | None = None) -> str:
        event = Event(
            name="device.refresh.requested",
            payload={"device_id": device_id},
        )

        self.context.event_bus.publish(event)
        return event.correlation_id

    def request_image_capture(self, device_id: str) -> str:
        event = Event(
            name="device.capture_image.requested",
            payload={"device_id": device_id},
        )

        self.context.event_bus.publish(event)
        return event.correlation_id

    def update_config(self, section: str, values: dict[str, Any]) -> None:
        self.context.config.update_section(section, values)

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def register_event_handlers(self) -> None:
        self.context.event_bus.subscribe(
            "device.refresh.completed",
            self.on_device_refresh_completed,
        )

    def on_device_refresh_completed(self, event: Event) -> None:
        # Later: notify RequestTracker.
        pass