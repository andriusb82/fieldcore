from __future__ import annotations

from typing import Any

from app.core.events import Event
from app.core.module import BaseModule


class AlarmManagerModule(BaseModule):
    name = "alarm_manager"
    config_section = "alarms"
    runner = "thread"

    @classmethod
    def default_config(cls) -> dict[str, Any]:
        return {
            "enabled": True,
            "runner": "thread",
            "rules": {
                "communication_lost": {
                    "enabled": True,
                    "timeout_seconds": 120,
                }
            },
        }

    def start(self) -> None:
        self.running = True

    def stop(self) -> None:
        self.running = False

    def raise_alarm(self, alarm_id: str, payload: dict[str, Any]) -> None:
        self.context.state.update_alarm_state(alarm_id, {
            "active": True,
            **payload,
        })

        self.context.event_bus.publish(Event(
            name="alarm.raised",
            payload={
                "alarm_id": alarm_id,
                **payload,
            },
        ))

    def clear_alarm(self, alarm_id: str, payload: dict[str, Any]) -> None:
        self.context.state.update_alarm_state(alarm_id, {
            "active": False,
            **payload,
        })

        self.context.event_bus.publish(Event(
            name="alarm.cleared",
            payload={
                "alarm_id": alarm_id,
                **payload,
            },
        ))

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def register_event_handlers(self) -> None:
        self.context.event_bus.subscribe(
            "device.data.received",
            self.on_device_data_received,
        )

    def on_device_data_received(self, event: Event) -> None:
        device_id = event.payload["device_id"]
        state = event.payload["state"]

        if not state.get("online", False):
            self.raise_alarm(
                alarm_id=f"{device_id}:offline",
                payload={"device_id": device_id},
            )
        else:
            self.clear_alarm(
                alarm_id=f"{device_id}:offline",
                payload={"device_id": device_id},
            )