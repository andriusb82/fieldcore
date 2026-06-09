from threading import Lock

from fieldcore.bus.simple_bus import SimpleBus
from fieldcore.transaction.result import TransactionResult
from fieldcore.transaction.transaction import Transaction


class RS485Bus(SimpleBus):
    def __init__(self, transport, protocol) -> None:
        super().__init__(transport, protocol)
        self._lock = Lock()

    def execute(self, transaction: Transaction) -> TransactionResult:
        with self._lock:
            return super().execute(transaction)
