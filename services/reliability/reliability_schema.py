def create_reliability_tables(storage):
    storage.execute("""
    CREATE TABLE IF NOT EXISTS state_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,

        owner_module TEXT NOT NULL,

        key TEXT NOT NULL UNIQUE,
        category TEXT NOT NULL,

        current_state TEXT NOT NULL,
        reported_state TEXT,

        pending_action TEXT NOT NULL,

        payload_json TEXT,

        correlation_id TEXT,

        version INTEGER NOT NULL DEFAULT 0,

        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        last_change_at TEXT NOT NULL,
        last_reported_at TEXT
    );
    """)

    storage.execute("""
    CREATE INDEX IF NOT EXISTS idx_state_pending
    ON state_items(pending_action);
    """)

    storage.execute("""
    CREATE INDEX IF NOT EXISTS idx_state_owner
    ON state_items(owner_module);
    """)

    storage.execute("""
    CREATE TABLE IF NOT EXISTS outbox_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,

        owner_module TEXT NOT NULL,

        message_type TEXT NOT NULL,
        target TEXT NOT NULL,

        payload_json TEXT NOT NULL,

        deduplication_key TEXT,
        correlation_id TEXT,

        status TEXT NOT NULL,

        priority INTEGER NOT NULL DEFAULT 100,

        retry_count INTEGER NOT NULL DEFAULT 0,
        max_retries INTEGER NOT NULL DEFAULT 10,

        next_retry_at TEXT,
        expires_at TEXT,

        created_at TEXT NOT NULL,
        sent_at TEXT,
        acknowledged_at TEXT,

        last_error TEXT
    );
    """)

    storage.execute("""
    CREATE INDEX IF NOT EXISTS idx_outbox_status
    ON outbox_messages(status);
    """)

    storage.execute("""
    CREATE INDEX IF NOT EXISTS idx_outbox_retry
    ON outbox_messages(next_retry_at);
    """)

    storage.execute("""
    CREATE INDEX IF NOT EXISTS idx_outbox_owner
    ON outbox_messages(owner_module);
    """)

    storage.execute("""
    CREATE TABLE IF NOT EXISTS operation_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,

        owner_module TEXT,

        operation_type TEXT,
        object_key TEXT,

        old_state TEXT,
        new_state TEXT,

        result TEXT,

        timestamp TEXT NOT NULL,

        details_json TEXT
    );
    """)
