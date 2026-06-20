import json
from datetime import datetime, timedelta, timezone

from fieldcore.services.reliability.constants import OutboxStatus


class OutboxService:

    def __init__(self, storage_service):
        self.storage = storage_service

    def enqueue(
        self,
        owner_module: str,
        message_type: str,
        target: str,
        payload: dict,
        deduplication_key: str | None = None,
        priority: int = 100,
        max_retries: int = 10,
    ):
        now = datetime.now(timezone.utc).isoformat()

        self.storage.execute(
            """
            INSERT INTO outbox_messages (
                owner_module, message_type, target, payload_json,
                deduplication_key, status, priority, retry_count,
                max_retries, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?, ?)
            """,
            (
                owner_module,
                message_type,
                target,
                json.dumps(payload),
                deduplication_key,
                OutboxStatus.PENDING,
                priority,
                max_retries,
                now,
            ),
        )

    def get_pending_messages(self, limit: int | None = None):
        now = datetime.now(timezone.utc).isoformat()

        sql = """
            SELECT * FROM outbox_messages
            WHERE status = ?
              AND (next_retry_at IS NULL OR next_retry_at <= ?)
            ORDER BY priority DESC, id ASC
        """
        params: list = [OutboxStatus.PENDING, now]

        if limit is not None:
            sql += " LIMIT ?"
            params.append(limit)

        rows = self.storage.query(sql, tuple(params))

        messages = []
        for row in rows:
            message = dict(row)
            message["payload"] = json.loads(message["payload_json"])
            messages.append(message)

        return messages

    def mark_sent(self, message_id: int):
        now = datetime.now(timezone.utc).isoformat()

        self.storage.execute(
            "UPDATE outbox_messages SET status = ?, sent_at = ? WHERE id = ?",
            (OutboxStatus.SENT, now, message_id),
        )

    def mark_failed(self, message_id: int, error: str, retry_delay_seconds: float = 0.0):
        row = self.storage.query_one(
            "SELECT retry_count, max_retries FROM outbox_messages WHERE id = ?",
            (message_id,),
        )

        if row is None:
            return

        new_retry_count = row["retry_count"] + 1
        is_exhausted = new_retry_count >= row["max_retries"]

        now = datetime.now(timezone.utc)
        next_retry_at = (now + timedelta(seconds=retry_delay_seconds)).isoformat()

        self.storage.execute(
            """
            UPDATE outbox_messages
            SET status = ?, retry_count = ?, last_error = ?, next_retry_at = ?
            WHERE id = ?
            """,
            (
                OutboxStatus.FAILED if is_exhausted else OutboxStatus.PENDING,
                new_retry_count,
                error,
                next_retry_at,
                message_id,
            ),
        )
