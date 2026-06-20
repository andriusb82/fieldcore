from __future__ import annotations

import sqlite3
from pathlib import Path
from threading import RLock

from fieldcore.logging_utils import get_logger


class SqliteStorage:
    def __init__(self, db_path: str | Path) -> None:
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: sqlite3.Connection | None = None
        self._lock = RLock()
        self.logger = get_logger(__name__)

    def connect(self) -> None:
        self._conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self.logger.info("Database connected", extra={"path": str(self._db_path)})

    def close(self) -> None:
        with self._lock:
            if self._conn:
                self._conn.close()
                self._conn = None

    def execute(self, sql: str, params: tuple = ()) -> int:
        with self._lock:
            assert self._conn is not None, "Database not connected"
            cursor = self._conn.execute(sql, params)
            self._conn.commit()
            return cursor.rowcount

    def insert(self, sql: str, params: tuple = ()) -> int:
        with self._lock:
            assert self._conn is not None, "Database not connected"
            cursor = self._conn.execute(sql, params)
            self._conn.commit()
            return cursor.lastrowid

    def query(self, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
        with self._lock:
            assert self._conn is not None, "Database not connected"
            cursor = self._conn.execute(sql, params)
            return cursor.fetchall()

    def query_one(self, sql: str, params: tuple = ()) -> sqlite3.Row | None:
        with self._lock:
            assert self._conn is not None, "Database not connected"
            cursor = self._conn.execute(sql, params)
            return cursor.fetchone()
