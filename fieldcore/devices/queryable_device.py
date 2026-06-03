from typing import Any

from fieldcore.logging_utils import get_logger
from fieldcore.protocol.base import BaseProtocol
from fieldcore.transport.base import BaseTransport


class QueryableDevice:
    def __init__(
        self,
        transport: BaseTransport,
        protocol: BaseProtocol,
    ) -> None:
        self.transport = transport
        self.protocol = protocol

        self.logger = get_logger(__name__)

    def query(self, command: str, **kwargs) -> Any:
        request = self.protocol.encode_request(command, **kwargs)

        self.logger.debug(
            "Sending device request",
            extra={
                "command": command,
                "request_size": len(request),
            },
        )

        self.transport.send(request)
        response = self.transport.read()

        self.logger.debug(
            "Received device response",
            extra={
                "command": command,
                "response_size": len(response),
            },
        )

        return self.protocol.decode_response(response)
