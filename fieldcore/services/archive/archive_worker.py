from __future__ import annotations

import threading
from typing import Any

from fieldcore.core.module import BaseModule
from fieldcore.logging_utils import get_logger
from fieldcore.services.archive.archive_service import ArchivePolicy, ArchiveService

logger = get_logger(__name__)


class ArchiveWorker(BaseModule):
    """
    Runs configured archive-move policies on an interval. Fully generic --
    table names, timestamp columns, and the age threshold all come from
    config, so this module carries no application-specific knowledge.
    """

    name = "archive"
    config_section = "archive"
    runner = "thread"

    @classmethod
    def default_config(cls) -> dict[str, Any]:
        return {
            "enabled": True,
            "check_interval_seconds": 3_600,
            "policies": [],
        }

    def __init__(self, config: dict[str, Any], context: Any) -> None:
        super().__init__(config, context)
        self._stop_event = threading.Event()

    def start(self) -> None:
        self.running = True
        self._stop_event.clear()

        logger.info("Archive worker started", extra={"policies": len(self.config["policies"])})

        while self.running:
            self._run_policies()
            self._stop_event.wait(timeout=self.config["check_interval_seconds"])

    def stop(self) -> None:
        self.running = False
        self._stop_event.set()

    def _run_policies(self) -> None:
        service = ArchiveService(self.context.storage)

        for raw_policy in self.config["policies"]:
            policy = ArchivePolicy(**raw_policy)
            try:
                service.move_aged_rows(policy)
            except Exception as exc:
                logger.warning(
                    "Archive policy failed",
                    extra={"source_table": policy.source_table, "error": str(exc)},
                )
