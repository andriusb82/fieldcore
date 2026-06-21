from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from fieldcore.logging_utils import get_logger

_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


@dataclass(slots=True)
class ArchivePolicy:
    source_table: str
    archive_table: str
    timestamp_column: str
    move_after_days: float

    def __post_init__(self) -> None:
        for identifier in (self.source_table, self.archive_table, self.timestamp_column):
            if not _IDENTIFIER_RE.match(identifier):
                raise ValueError(f"Unsafe SQL identifier in archive policy: {identifier!r}")


class ArchiveService:
    """
    Moves aged-out rows from a 'hot' table into a same-schema archive
    table, keeping the hot table small and fast while preserving history
    for later retention/export. The archive table is created automatically
    (if missing) by copying the source table's schema, so callers never
    hand-write a second CREATE TABLE statement.

    Note: the archive table's schema is captured once, at first creation.
    If the source table's schema changes later, the archive table is not
    automatically migrated.
    """

    def __init__(self, storage) -> None:
        self.storage = storage
        self.logger = get_logger(__name__)

    def ensure_archive_table(self, policy: ArchivePolicy) -> None:
        self.storage.execute(
            f"CREATE TABLE IF NOT EXISTS {policy.archive_table} "
            f"AS SELECT * FROM {policy.source_table} WHERE 0"
        )

    def move_aged_rows(self, policy: ArchivePolicy) -> int:
        self.ensure_archive_table(policy)

        cutoff = (
            datetime.now(timezone.utc) - timedelta(days=policy.move_after_days)
        ).isoformat()

        with self.storage.transaction() as conn:
            conn.execute(
                f"INSERT INTO {policy.archive_table} "
                f"SELECT * FROM {policy.source_table} WHERE {policy.timestamp_column} < ?",
                (cutoff,),
            )
            cursor = conn.execute(
                f"DELETE FROM {policy.source_table} WHERE {policy.timestamp_column} < ?",
                (cutoff,),
            )
            moved = cursor.rowcount

        self.logger.info(
            "Archive policy applied",
            extra={
                "source_table": policy.source_table,
                "archive_table": policy.archive_table,
                "moved": moved,
                "cutoff": cutoff,
            },
        )

        return moved
