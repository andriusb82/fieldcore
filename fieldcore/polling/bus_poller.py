from __future__ import annotations

import threading
import time
from collections.abc import Callable
from typing import Any

from fieldcore.bus.base import BaseBus
from fieldcore.logging_utils import get_logger
from fieldcore.polling.polling_slot import PollingSlot
from fieldcore.transaction.transaction import Transaction
from fieldcore.transaction.result import TransactionResult


PollResultHandler = Callable[[PollingSlot, TransactionResult], None]


class BusPoller:
    def __init__(
        self,
        bus: BaseBus,
        interval: float = 0.1,
        on_result: PollResultHandler | None = None,
    ) -> None:
        self.bus = bus
        self.interval = interval
        self.on_result = on_result

        self.slots: list[PollingSlot] = []
        self.running = False
        self._thread: threading.Thread | None = None
        self._last_poll: dict[str, float] = {}

        self.logger = get_logger(__name__)

    def add_slot(self, slot: PollingSlot) -> None:
        self.slots.append(slot)

    def remove_slot(self, device_id: str, command: str | None = None) -> None:
        self.slots = [
            slot
            for slot in self.slots
            if not (
                slot.device_id == device_id
                and (command is None or slot.command == command)
            )
        ]

    def start(self) -> None:
        if self.running:
            return

        self.running = True
        self._thread = threading.Thread(
            target=self._run,
            name="BusPoller",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        self.running = False

        if self._thread:
            self._thread.join(timeout=5.0)
            self._thread = None

    def _run(self) -> None:
        while self.running:
            now = time.monotonic()

            for slot in sorted(self.slots, key=lambda item: item.priority, reverse=True):
                if not self.running:
                    break

                if not slot.enabled:
                    continue

                key = self._slot_key(slot)
                last_poll = self._last_poll.get(key, 0.0)

                if now - last_poll < slot.interval:
                    continue

                self._last_poll[key] = now
                result = self._poll_slot(slot)

                if self.on_result:
                    self.on_result(slot, result)

            time.sleep(self.interval)

    def _poll_slot(self, slot: PollingSlot) -> TransactionResult:
        transaction = Transaction(
            command=slot.command,
            payload=slot.payload,
            timeout=slot.timeout,
            retries=slot.retries,
            priority=slot.priority,
        )

        self.logger.debug(
            "Polling bus slot",
            extra={
                "device_id": slot.device_id,
                "command": slot.command,
            },
        )

        return self.bus.execute(transaction)

    def _slot_key(self, slot: PollingSlot) -> str:
        return f"{slot.device_id}:{slot.command}"
