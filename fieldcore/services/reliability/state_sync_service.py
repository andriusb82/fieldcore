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
        pass

    def get_pending_items(self):
        pass

    def mark_reported(
        self,
        key: str,
        reported_state: str,
    ):
        pass
