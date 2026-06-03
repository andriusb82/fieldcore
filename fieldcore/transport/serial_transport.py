import serial

from fieldcore.logging_utils import get_logger
from fieldcore.transport.base import BaseTransport, TransportError


class SerialTransport(BaseTransport):
    def __init__(
        self,
        port: str,
        baudrate: int = 9600,
        timeout: float = 1.0,
        auto_reconnect: bool = True,
    ) -> None:
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.auto_reconnect = auto_reconnect
        self._serial: serial.Serial | None = None

        self.logger = get_logger(__name__)

    def connect(self) -> None:
        try:
            self._serial = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.timeout,
            )

            self.logger.info(
                "Serial connection established",
                extra={
                    "port": self.port,
                    "baudrate": self.baudrate,
                },
            )

        except Exception as error:
            self.logger.exception("Failed to connect serial transport")
            raise TransportError(str(error)) from error

    def close(self) -> None:
        if self._serial:
            self._serial.close()
            self._serial = None

    def reconnect(self) -> None:
        self.logger.warning("Reconnecting serial transport")
        self.close()
        self.connect()

    def is_connected(self) -> bool:
        return self._serial is not None and self._serial.is_open

    def send(self, data: bytes) -> None:
        try:
            self.ensure_connected()
            assert self._serial is not None
            self._serial.write(data)

        except Exception as error:
            self.logger.exception("Serial send failed")

            if self.auto_reconnect:
                self.reconnect()

            raise TransportError(str(error)) from error

    def read(self, size: int = 1024) -> bytes:
        try:
            self.ensure_connected()
            assert self._serial is not None
            return self._serial.read(size)

        except Exception as error:
            self.logger.exception("Serial read failed")

            if self.auto_reconnect:
                self.reconnect()

            raise TransportError(str(error)) from error

    def ensure_connected(self) -> None:
        if not self.is_connected():
            self.connect()
