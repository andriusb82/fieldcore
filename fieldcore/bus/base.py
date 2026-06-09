from __future__ import annotations

from abc import ABC, abstractmethod

from fieldcore.protocol.base import BaseProtocol
from fieldcore.transaction.transaction import Transaction
from fieldcore.transaction.result import TransactionResult
from fieldcore.transport.base import BaseTransport


class BaseBus(ABC):
    def __init__(
        self,
        transport: BaseTransport,
        protocol: BaseProtocol,
    ) -> None:
        self.transport = transport
        self.protocol = protocol

    @abstractmethod
    def execute(self, transaction: Transaction) -> TransactionResult:
        pass
