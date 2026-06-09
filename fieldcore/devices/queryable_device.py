from typing import Any

from fieldcore.bus.base import BaseBus
from fieldcore.logging_utils import get_logger
from fieldcore.transaction.transaction import Transaction


class QueryableDevice:
    def __init__(
        self,
        bus: BaseBus,
    ) -> None:
        self.bus = bus
        self.logger = get_logger(__name__)

    def query(self, command: str, **kwargs) -> Any:
        transaction = Transaction(
            command=command,
            payload=kwargs,
        )

        self.logger.debug(
            "Executing device transaction",
            extra={
                "command": command,
            },
        )

        result = self.bus.execute(transaction)

        if not result.ok:
            raise RuntimeError(result.error)

        return result.response
