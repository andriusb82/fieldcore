from fieldcore.bus.base import BaseBus
from fieldcore.transaction.result import TransactionResult
from fieldcore.transaction.transaction import Transaction


class SimpleBus(BaseBus):
    def execute(self, transaction: Transaction) -> TransactionResult:
        request = self.protocol.encode_request(
            transaction.command,
            **transaction.payload,
        )

        try:
            self.transport.send(request)
            response = self.transport.read()

            decoded = self.protocol.decode_response(response)

            return TransactionResult(
                ok=True,
                response=decoded,
            )

        except Exception as error:
            return TransactionResult(
                ok=False,
                error=str(error),
            )
