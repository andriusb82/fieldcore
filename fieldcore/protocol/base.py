from abc import ABC, abstractmethod
from typing import Any


class BaseProtocol(ABC):
    @abstractmethod
    def encode_request(self, command: str, **kwargs) -> bytes:
        pass

    @abstractmethod
    def decode_response(self, data: bytes) -> Any:
        pass
