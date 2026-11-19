from __future__ import annotations

from typing import Any, Callable

from fieldcore.alarms.alarm_manager import ALARM_CLEAR_REQUESTED, ALARM_RAISE_REQUESTED
from fieldcore.core.events import Event, LocalEventBus

SendFn = Callable[[dict[str, Any], str], None]


class ConnectivityMonitor:
    """Detects connectivity loss/restoration from send outcomes.

    fieldcore has no connectivity-lost/-restored concept anywhere else in the
    library - the closest primitives are transport-level auto-reconnect-on-failure
    and the outbox's per-message backoff, neither of which distinguishes "one
    message failed" from "the link is down." This wraps a send_fn to count
    *consecutive* failures across calls and raises/clears a single alarm (by the
    id given at construction) plus a "connectivity.restored" event on the
    down/up transitions - via the generic alarm.raise.requested/
    alarm.clear.requested events AlarmManagerModule listens for, so this has no
    direct coupling to whichever AlarmManagerModule instance is running.

    One monitor tracks one logical link - construct a separate instance (with
    a distinct alarm_id) per outbound connection if an application has more
    than one.
    """

    def __init__(
        self,
        event_bus: LocalEventBus,
        alarm_id: str,
        failure_threshold: int = 3,
    ) -> None:
        self.event_bus = event_bus
        self.alarm_id = alarm_id
        self.failure_threshold = failure_threshold
        self._consecutive_failures = 0
        self._down = False

    @property
    def is_down(self) -> bool:
        return self._down

    def wrap(self, send_fn: SendFn) -> SendFn:
        def wrapped(payload: dict[str, Any], message_type: str) -> None:
            try:
                send_fn(payload, message_type)
            except Exception:
                self.record_failure()
                raise
            else:
                self.record_success()

        return wrapped

    def record_failure(self) -> None:
        self._consecutive_failures += 1

        if not self._down and self._consecutive_failures >= self.failure_threshold:
            self._down = True
            self.event_bus.publish(Event(
                name=ALARM_RAISE_REQUESTED,
                payload={"alarm_id": self.alarm_id},
            ))

    def record_success(self) -> None:
        was_down = self._down
        self._consecutive_failures = 0

        if not was_down:
            return

        self._down = False
        self.event_bus.publish(Event(
            name=ALARM_CLEAR_REQUESTED,
            payload={"alarm_id": self.alarm_id},
        ))
        self.event_bus.publish(Event(name="connectivity.restored", payload={}))
