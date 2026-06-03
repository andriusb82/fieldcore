import socket

from fieldcore.logging_utils import get_logger
from fieldcore.transport.base import BaseTransport, TransportError


class TcpTransport(BaseTransport):
    def __init__(
        self,
        host: str,
        port: int,
        timeout: float = 1.0,
        auto_reconnect: bool = True,
    ) -> None:
        self.host = host
        self.port = port
        self.timeout = timeout
        self.auto_reconnect = auto_reconnect
        self._socket: socket.socket | None = None

        self.logger = get_logger(__name__)

    def connect(self) -> None:
        try:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._socket.settimeout(self.timeout)
            self._socket.connect((self.host, self.port))

            self.logger.info(
                "TCP connection established",
                extra={
                    "host": self.host,
                    "port": self.port,
                },
            )

        except Exception as error:
            self.logger.exception("Failed to connect TCP transport")
            raise TransportError(str(error)) from error

    def close(self) -> None:
        if self._socket:
            self._socket.close()
            self._socket = None

    def reconnect(self) -> None:
        self.logger.warning("Reconnecting TCP transport")
        self.close()
        self.connect()

    def is_connected(self) -> bool:
        return self._socket is not None

    def send(self, data: bytes) -> None:
        try:
            self.ensure_connected()
            assert self._socket is not None
            self._socket.sendall(data)

        except Exception as error:
            self.logger.exception("TCP send failed")

            if self.auto_reconnect:
                self.reconnect()

            raise TransportError(str(error)) from error

    def read(self, size: int = 1024) -> bytes:
        try:
            self.ensure_connected()
            assert self._socket is not None
            return self._socket.recv(size)

        except Exception as error:
            self.logger.exception("TCP read failed")

            if self.auto_reconnect:
                self.reconnect()

            raise TransportError(str(error)) from error

    def ensure_connected(self) -> None:
        if not self.is_connected():
            self.connect()
