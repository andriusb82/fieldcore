from typing import Any

from fieldcore.transport.serial_transport import SerialTransport
from fieldcore.transport.tcp_transport import TcpTransport


def create_transport(config: dict[str, Any]):
    transport_type = config["type"].lower()

    if transport_type in ("rs232", "rs485", "serial"):
        return SerialTransport(
            port=config["port"],
            baudrate=config.get("baudrate", 9600),
            timeout=config.get("timeout", 1.0),
            auto_reconnect=config.get("auto_reconnect", True),
        )

    if transport_type == "tcp":
        return TcpTransport(
            host=config["host"],
            port=config["port"],
            timeout=config.get("timeout", 1.0),
            auto_reconnect=config.get("auto_reconnect", True),
        )

    raise ValueError(f"Unsupported transport type: {transport_type}")
