from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from typing import Any

from fieldcore.core.events import Event
from fieldcore.core.module import BaseModule
from fieldcore.logging_utils import get_logger


class AlarmManagerModule(BaseModule):
    """
    Generic alarm lifecycle engine.

    Callers raise/clear alarms by id. An alarm is considered active from the
    first raise_alarm() call until either clear_alarm() is called explicitly,
    or it is not refreshed (re-raised) within its timeout window, in which
    case it is auto-cleared. Every SET/CLEAR transition is persisted to the
    'alarms' table and enqueued to the outbox for delivery to the remote
    system. Active alarms are restored from the database on startup so a
    restart does not lose alarm state.
    """

    name = "alarm_manager"
    config_section = "alarms"
    runner = "thread"

    @classmethod
    def default_config(cls) -> dict[str, Any]:
        return {
            "enabled": True,
            "runner": "thread",
            "check_interval_seconds": 5,
            "default_timeout_seconds": 120,
            "watch_device_offline": True,
            "outbox_target": "central_system",
        }

    def __init__(self, config: dict[str, Any], context: Any) -> None:
        super().__init__(config, context)
        self._active: dict[str, dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self.logger = get_logger(__name__)

    def start(self) -> None:
        self.running = True
        self._stop_event.clear()
        self._restore_active_alarms()

        while self.running:
            self._sweep_expired()
            self._stop_event.wait(timeout=self.config["check_interval_seconds"])

    def stop(self) -> None:
        self.running = False
        self._stop_event.set()

    def health(self) -> dict[str, Any]:
        with self._lock:
            active_count = len(self._active)

        return {
            "name": self.name,
            "running": self.running,
            "active_alarms": active_count,
        }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def raise_alarm(
        self,
        alarm_id: str,
        payload: dict[str, Any] | None = None,
        timeout_seconds: float | None = None,
    ) -> None:
        payload = payload or {}
        now = datetime.now(timezone.utc)
        timeout = (
            timeout_seconds
            if timeout_seconds is not None
            else self.config["default_timeout_seconds"]
        )

        with self._lock:
            is_new = alarm_id not in self._active
            self._active[alarm_id] = {
                "payload": payload,
                "last_seen": now,
                "timeout_seconds": timeout,
            }

        self.context.state.update_alarm_state(alarm_id, {
            "active": True,
            "last_seen": now.isoformat(),
            **payload,
        })

        if not is_new:
            return

        self._persist("SET", alarm_id, payload)
        self._enqueue("alarm.raised", alarm_id, payload)

        self.context.event_bus.publish(Event(
            name="alarm.raised",
            payload={"alarm_id": alarm_id, **payload},
        ))

        self.logger.info("Alarm raised", extra={"alarm_id": alarm_id})

    def clear_alarm(self, alarm_id: str, payload: dict[str, Any] | None = None) -> None:
        payload = payload or {}

        with self._lock:
            existed = self._active.pop(alarm_id, None) is not None

        if not existed:
            return

        self.context.state.update_alarm_state(alarm_id, {
            "active": False,
            **payload,
        })

        self._persist("CLEAR", alarm_id, payload)
        self._enqueue("alarm.cleared", alarm_id, payload)

        self.context.event_bus.publish(Event(
            name="alarm.cleared",
            payload={"alarm_id": alarm_id, **payload},
        ))

        self.logger.info("Alarm cleared", extra={"alarm_id": alarm_id})

    def get_active_alarms(self) -> dict[str, dict[str, Any]]:
        with self._lock:
            return {
                alarm_id: dict(entry["payload"])
                for alarm_id, entry in self._active.items()
            }

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _sweep_expired(self) -> None:
        now = datetime.now(timezone.utc)
        expired: list[tuple[str, dict[str, Any]]] = []

        with self._lock:
            for alarm_id, entry in self._active.items():
                age = (now - entry["last_seen"]).total_seconds()
                if age > entry["timeout_seconds"]:
                    expired.append((alarm_id, entry["payload"]))

        for alarm_id, payload in expired:
            self.clear_alarm(alarm_id, payload)

    def _persist(self, action: str, alarm_id: str, payload: dict[str, Any]) -> None:
        now = datetime.now(timezone.utc).isoformat()

        self.context.storage.execute(
            """
            INSERT INTO alarms (alarm_id, action, payload_json, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (alarm_id, action, json.dumps(payload), now),
        )

    def _enqueue(self, message_type: str, alarm_id: str, payload: dict[str, Any]) -> None:
        self.context.outbox.enqueue(
            owner_module=self.name,
            message_type=message_type,
            target=self.config["outbox_target"],
            payload={"alarm_id": alarm_id, **payload},
        )

    def _restore_active_alarms(self) -> None:
        rows = self.context.storage.query(
            """
            SELECT a.alarm_id, a.payload_json
            FROM alarms a
            WHERE a.action = 'SET'
              AND NOT EXISTS (
                  SELECT 1 FROM alarms b
                  WHERE b.alarm_id = a.alarm_id
                    AND b.action = 'CLEAR'
                    AND b.id > a.id
              )
            """
        )

        now = datetime.now(timezone.utc)

        with self._lock:
            for row in rows:
                self._active[row["alarm_id"]] = {
                    "payload": json.loads(row["payload_json"] or "{}"),
                    "last_seen": now,
                    "timeout_seconds": self.config["default_timeout_seconds"],
                }

        if rows:
            self.logger.info("Restored active alarms", extra={"count": len(rows)})

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def register_event_handlers(self) -> None:
        if self.config.get("watch_device_offline", True):
            self.context.event_bus.subscribe(
                "device.data.received",
                self.on_device_data_received,
            )

    def on_device_data_received(self, event: Event) -> None:
        device_id = event.payload["device_id"]
        state = event.payload["state"]

        if not state.get("online", False):
            self.raise_alarm(f"{device_id}:offline", {"device_id": device_id})
        else:
            self.clear_alarm(f"{device_id}:offline", {"device_id": device_id})
