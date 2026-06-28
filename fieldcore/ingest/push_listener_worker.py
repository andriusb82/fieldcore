from __future__ import annotations

import threading
from typing import Any, Callable

from fieldcore.core.module import BaseModule
from fieldcore.ingest.http_push_listener import DataHandler, HttpPushListener
from fieldcore.logging_utils import get_logger

StaleHandler = Callable[[], None]

logger = get_logger(__name__)


class PushListenerWorker(BaseModule):
    """
    Wraps HttpPushListener with staleness detection: if no request arrives
    within restart_timeout_seconds, on_stale() fires and the listener is
    torn down and restarted (matching the watchdog behaviour field devices
    like cabinet monitors need — a wedged socket otherwise looks identical
    to "device stopped reporting").

    on_data and on_stale carry all application-specific behaviour; this
    module has no knowledge of what the data means.
    """

    name = "push_listener"
    config_section = "push_listener"
    runner = "thread"

    @classmethod
    def default_config(cls) -> dict[str, Any]:
        return {
            "enabled": True,
            "host": "0.0.0.0",
            "port": 8001,
            "field_map": {},
            "restart_timeout_seconds": 60,
            "check_interval_seconds": 5,
        }

    def __init__(
        self,
        config: dict[str, Any],
        context: Any,
        on_data: DataHandler,
        on_stale: StaleHandler | None = None,
    ) -> None:
        super().__init__(config, context)
        self._stop_event = threading.Event()
        self._listener: HttpPushListener | None = None
        self._on_data = on_data
        self._on_stale = on_stale or (lambda: None)

    def start(self) -> None:
        self.running = True
        self._stop_event.clear()
        self._start_listener()

        while self.running:
            self._check_staleness()
            self._stop_event.wait(timeout=self.config["check_interval_seconds"])

    def stop(self) -> None:
        self.running = False
        self._stop_event.set()

        if self._listener:
            self._listener.stop()
            self._listener = None

    def _start_listener(self) -> None:
        self._listener = HttpPushListener(
            host=self.config["host"],
            port=self.config["port"],
            field_map=self.config["field_map"],
            on_data=self._on_data,
        )
        self._listener.start()

    def _check_staleness(self) -> None:
        if self._listener is None:
            return

        age = self._listener.seconds_since_last_request()
        timeout = self.config["restart_timeout_seconds"]

        if age is not None and age > timeout:
            logger.warning("Push listener stale, restarting", extra={"age_seconds": age})

            try:
                self._on_stale()
            except Exception:
                logger.exception("on_stale handler raised")

            self._listener.stop()
            self._start_listener()
