from __future__ import annotations

from queue import Empty, Queue
from typing import Any

from fieldcore.core.events import Event
from fieldcore.core.module import BaseModule


class DeviceWorkerModule(BaseModule):
    name = "device_worker"
    config_section = "devices"
    runner = "thread"

    command_queue: Queue[Event]

    @classmethod
    def default_config(cls) -> dict[str, Any]:
        return {
            "enabled": True,
            "runner": "thread",
            "poll_interval_seconds": 30,
            "devices": [
                {
                    "id": "sensor_01",
                    "type": "example_tcp",
                    "host": "192.168.1.50",
                    "port": 4001,
                }
            ],
        }

    def __init__(self, config: dict[str, Any], context: "AppContext") -> None:
        super().__init__(config, context)
        self.command_queue = Queue()
        self.poll_interval_seconds = config["poll_interval_seconds"]
        self.context.command_bus.register_queue(self.name, self.command_queue)

    def start(self) -> None:
        self.running = True

        while self.running:
            try:
                command = self.command_queue.get(timeout=self.poll_interval_seconds)
                self._handle_command(command)
            except Empty:
                self.refresh_all(reason="scheduled")

    def stop(self) -> None:
        self.running = False

    def refresh_all(self, reason: str) -> None:
        for device in self.config.get("devices", []):
            self.refresh_device(device["id"], reason=reason)

    def refresh_device(self, device_id: str, reason: str) -> None:
        # Later: select correct driver by device type.
        state = {
            "device_id": device_id,
            "online": True,
            "reason": reason,
        }

        self.context.state.update_device_state(device_id, state)

        self.context.event_bus.publish(Event(
            name="device.data.received",
            payload={
                "device_id": device_id,
                "state": state,
                "reason": reason,
            },
        ))

    def capture_image(self, device_id: str) -> None:
        image_info = {
            "device_id": device_id,
            "path": f"data/images/{device_id}/latest.jpg",
            "mime_type": "image/jpeg",
        }

        self.context.event_bus.publish(Event(
            name="device.image.received",
            payload=image_info,
        ))

    def apply_config(self, new_config: dict[str, Any]) -> None:
        super().apply_config(new_config)
        self.poll_interval_seconds = new_config["poll_interval_seconds"]

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def register_event_handlers(self) -> None:
        self.context.event_bus.subscribe(
            "device.refresh.requested",
            self.on_device_refresh_requested,
        )
        self.context.event_bus.subscribe(
            "device.capture_image.requested",
            self.on_device_capture_image_requested,
        )

    def on_device_refresh_requested(self, event: Event) -> None:
        self.command_queue.put(event)

    def on_device_capture_image_requested(self, event: Event) -> None:
        self.command_queue.put(event)

    def _handle_command(self, command: Event) -> None:
        if command.name == "device.refresh.requested":
            device_id = command.payload.get("device_id")

            if device_id:
                self.refresh_device(device_id, reason="requested")
            else:
                self.refresh_all(reason="requested")

            self.context.event_bus.publish(Event(
                name="device.refresh.completed",
                payload={
                    "device_id": device_id,
                    "correlation_id": command.correlation_id,
                },
                correlation_id=command.correlation_id,
            ))

        elif command.name == "device.capture_image.requested":
            self.capture_image(command.payload["device_id"])