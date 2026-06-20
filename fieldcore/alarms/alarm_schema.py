def create_alarm_tables(storage) -> None:
    storage.execute("""
    CREATE TABLE IF NOT EXISTS alarms (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        alarm_id    TEXT    NOT NULL,
        action      TEXT    NOT NULL,
        payload_json TEXT,
        created_at  TEXT    NOT NULL
    )
    """)

    storage.execute("""
    CREATE INDEX IF NOT EXISTS idx_alarms_alarm_id_created
    ON alarms (alarm_id, created_at)
    """)
