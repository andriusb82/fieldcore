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
    ):
        pass

    def get_pending_messages(self):
        pass

    def mark_sent(self, message_id: int):
        pass

    def mark_failed(self, message_id: int, error: str):
        pass
