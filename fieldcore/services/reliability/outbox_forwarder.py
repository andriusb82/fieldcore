from __future__ import annotations

import time
from typing import Any, Callable

from fieldcore.logging_utils import get_logger
from fieldcore.services.reliability.outbox_service import OutboxService

SendFn = Callable[[dict[str, Any]], None]


class OutboxForwarder:
    """
    Drains pending outbox messages in batches, sending each through send_fn.
    Generic over transport — send_fn raises on failure, returns normally on
    success. Failures get exponential backoff (capped) via next_retry_at,
    so a struggling endpoint is retried with growing delay instead of being
    hammered every cycle.
    """

    def __init__(
        self,
        outbox: OutboxService,
        send_fn: SendFn,
        batch_size: int = 50,
        batch_delay_seconds: float = 0.0,
        backoff_base_seconds: float = 5.0,
        backoff_max_seconds: float = 300.0,
    ) -> None:
        self.outbox = outbox
        self.send_fn = send_fn
        self.batch_size = batch_size
        self.batch_delay_seconds = batch_delay_seconds
        self.backoff_base_seconds = backoff_base_seconds
        self.backoff_max_seconds = backoff_max_seconds
        self.logger = get_logger(__name__)

    def flush(self) -> int:
        messages = self.outbox.get_pending_messages(limit=self.batch_size)
        sent_count = 0

        for message in messages:
            if self._send_one(message):
                sent_count += 1

            if self.batch_delay_seconds:
                time.sleep(self.batch_delay_seconds)

        return sent_count

    def _send_one(self, message: dict[str, Any]) -> bool:
        try:
            self.send_fn(message["payload"])
            self.outbox.mark_sent(message["id"])
            return True

        except Exception as exc:
            delay = min(
                self.backoff_base_seconds * (2 ** message["retry_count"]),
                self.backoff_max_seconds,
            )
            self.outbox.mark_failed(message["id"], str(exc), retry_delay_seconds=delay)

            self.logger.warning(
                "Outbox message failed",
                extra={
                    "message_id": message["id"],
                    "retry_count": message["retry_count"] + 1,
                    "next_retry_in_seconds": delay,
                    "error": str(exc),
                },
            )
            return False
