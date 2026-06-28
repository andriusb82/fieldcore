import json
from datetime import datetime, timezone

from fieldcore.services.reliability.constants import PendingAction


class StateSyncService:

    def __init__(self, storage_service):
        self.storage = storage_service

    def set_state(
        self,
        owner_module: str,
        key: str,
        category: str,
        current_state: str,
        payload: dict | None = None,
    ):
        now = datetime.now(timezone.utc).isoformat()
        payload_json = json.dumps(payload or {})

        existing = self.storage.query(
            "SELECT id, current_state FROM state_items WHERE key = ?",
            (key,),
        )

        if existing:
            row = existing[0]

            if row["current_state"] == current_state:
                return

            self.storage.execute(
                """
                UPDATE state_items
                SET current_state = ?, payload_json = ?, pending_action = ?,
                    version = version + 1, updated_at = ?, last_change_at = ?
                WHERE id = ?
                """,
                (
                    current_state,
                    payload_json,
                    PendingAction.SEND_ACTIVE,
                    now,
                    now,
                    row["id"],
                ),
            )
        else:
            self.storage.execute(
                """
                INSERT INTO state_items (
                    owner_module, key, category, current_state,
                    pending_action, payload_json, version,
                    created_at, updated_at, last_change_at
                ) VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?, ?)
                """,
                (
                    owner_module,
                    key,
                    category,
                    current_state,
                    PendingAction.SEND_ACTIVE,
                    payload_json,
                    now,
                    now,
                    now,
                ),
            )

    def get_pending_items(self):
        rows = self.storage.query(
            "SELECT * FROM state_items WHERE pending_action != ?",
            (PendingAction.NONE,),
        )

        items = []
        for row in rows:
            item = dict(row)
            item["payload"] = json.loads(item["payload_json"]) if item["payload_json"] else {}
            items.append(item)

        return items

    def mark_reported(
        self,
        key: str,
        reported_state: str,
    ):
        now = datetime.now(timezone.utc).isoformat()

        self.storage.execute(
            """
            UPDATE state_items
            SET reported_state = ?, pending_action = ?, last_reported_at = ?
            WHERE key = ?
            """,
            (reported_state, PendingAction.NONE, now, key),
        )
