from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from fieldcore.logging_utils import get_logger

_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


@dataclass(slots=True)
class RetentionPolicy:
    table: str
    timestamp_column: str
    max_age_days: float

    def __post_init__(self) -> None:
        for identifier in (self.table, self.timestamp_column):
            if not _IDENTIFIER_RE.match(identifier):
                raise ValueError(f"Unsafe SQL identifier in retention policy: {identifier!r}")


class RetentionService:
    """
    Generic age-based row deletion. Table and column names are supplied by
    the caller via RetentionPolicy, so this has no knowledge of any
    application's schema.
    """

    def __init__(self, storage) -> None:
        self.storage = storage
        self.logger = get_logger(__name__)

    def apply(self, policy: RetentionPolicy) -> int:
        cutoff = (
            datetime.now(timezone.utc) - timedelta(days=policy.max_age_days)
        ).isoformat()

        deleted = self.storage.execute(
            f"DELETE FROM {policy.table} WHERE {policy.timestamp_column} < ?",
            (cutoff,),
        )

        self.logger.info(
            "Retention policy applied",
            extra={"table": policy.table, "deleted": deleted, "cutoff": cutoff},
        )

        return deleted

    def vacuum(self) -> None:
        self.storage.execute("VACUUM")
        self.storage.execute("PRAGMA optimize")
        self.logger.info("Database vacuumed and optimized")
