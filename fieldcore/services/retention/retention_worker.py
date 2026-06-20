from __future__ import annotations

import threading
from typing import Any

from fieldcore.core.module import BaseModule
from fieldcore.logging_utils import get_logger
from fieldcore.services.retention.retention_service import RetentionPolicy, RetentionService

logger = get_logger(__name__)


class RetentionWorker(BaseModule):
    """
    Runs configured age-based retention policies on an interval, then
    optionally vacuums the database. Fully generic — table names and
    retention windows come from config, so this module carries no
    application-specific knowledge.
    """

    name = "retention"
    config_section = "retention"
    runner = "thread"

    @classmethod
    def default_config(cls) -> dict[str, Any]:
        return {
            "enabled": True,
            "check_interval_seconds": 86_400,
            "vacuum_on_run": True,
            "policies": [],
        }

    def __init__(self, config: dict[str, Any], context: Any) -> None:
        super().__init__(config, context)
        self._stop_event = threading.Event()

    def start(self) -> None:
        self.running = True
        self._stop_event.clear()

        logger.info("Retention worker started", extra={"policies": len(self.config["policies"])})

        while self.running:
            self._run_policies()
            self._stop_event.wait(timeout=self.config["check_interval_seconds"])

    def stop(self) -> None:
        self.running = False
        self._stop_event.set()

    def _run_policies(self) -> None:
        service = RetentionService(self.context.storage)

        for raw_policy in self.config["policies"]:
            policy = RetentionPolicy(**raw_policy)
            try:
                service.apply(policy)
            except Exception as exc:
                logger.warning("Retention policy failed", extra={"table": policy.table, "error": str(exc)})

        if self.config.get("vacuum_on_run", True):
            service.vacuum()
