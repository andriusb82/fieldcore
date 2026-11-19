from __future__ import annotations

import threading
from typing import Any

from fieldcore.core.module import BaseModule
from fieldcore.logging_utils import get_logger
from fieldcore.services.reliability.outbox_forwarder import OutboxForwarder
from fieldcore.services.reliability.outbox_service import OutboxService

logger = get_logger(__name__)


class OutboxForwarderWorker(BaseModule):
    """Drives OutboxForwarder.flush() on an interval - fieldcore ships the
    enqueue/dequeue/backoff/batch mechanics (OutboxService/OutboxForwarder) but
    nothing that actually schedules flush(), following the
    ArchiveWorker/RetentionWorker scheduling pattern.

    Expects context.storage (the shared storage service) and
    context.outbox_send_fn: (payload, message_type) -> None - the actual
    transport, already wrapped with whatever retry/connectivity logic the
    application needs (e.g. ConnectivityMonitor.wrap()) before being placed
    on context. This module has no knowledge of what's on the other end.
    """

    name = "outbox_forwarder"
    config_section = "outbox_forwarder"
    runner = "thread"

    @classmethod
    def default_config(cls) -> dict[str, Any]:
        return {
            "enabled": True,
            "check_interval_seconds": 30,
            "batch_size": 50,
            "batch_delay_seconds": 0.0,
            "backoff_base_seconds": 5.0,
            "backoff_max_seconds": 300.0,
        }

    def __init__(self, config: dict[str, Any], context: Any) -> None:
        super().__init__(config, context)
        self._stop_event = threading.Event()
        self._forwarder = OutboxForwarder(
            outbox=OutboxService(context.storage),
            send_fn=context.outbox_send_fn,
            batch_size=config["batch_size"],
            batch_delay_seconds=config["batch_delay_seconds"],
            backoff_base_seconds=config["backoff_base_seconds"],
            backoff_max_seconds=config["backoff_max_seconds"],
        )

    def start(self) -> None:
        self.running = True
        self._stop_event.clear()

        while self.running:
            try:
                self._forwarder.flush()
            except Exception:
                logger.exception("Outbox flush failed unexpectedly")

            self._stop_event.wait(timeout=self.config["check_interval_seconds"])

    def stop(self) -> None:
        self.running = False
        self._stop_event.set()
