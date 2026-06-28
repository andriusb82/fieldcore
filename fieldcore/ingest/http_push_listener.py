from __future__ import annotations

import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Callable
from urllib.parse import parse_qs, urlparse

from fieldcore.logging_utils import get_logger

DataHandler = Callable[[dict[str, str]], None]


class HttpPushListener:
    """
    Generic receiver for field devices that report data by making periodic
    HTTP GET requests with query-string parameters (e.g. a control cabinet
    monitor unit), as opposed to devices that get polled by us.

    field_map translates query parameter names to caller-defined field
    names, e.g. {"field1": "battery_voltage"}. on_data(dict) is called with
    the mapped values (still raw strings — value parsing/validation is the
    caller's concern) on every request. seconds_since_last_request() lets a
    caller implement its own staleness detection.
    """

    def __init__(
        self,
        host: str,
        port: int,
        field_map: dict[str, str],
        on_data: DataHandler,
    ) -> None:
        self.host = host
        self.port = port
        self.field_map = field_map
        self.on_data = on_data

        self._last_request_at: float | None = None
        self._lock = threading.Lock()
        self._httpd: HTTPServer | None = None
        self._thread: threading.Thread | None = None
        self.logger = get_logger(__name__)

    def start(self) -> None:
        handler_cls = self._build_handler_class()

        self._httpd = HTTPServer((self.host, self.port), handler_cls)
        self._httpd.allow_reuse_address = True

        self._thread = threading.Thread(
            target=self._httpd.serve_forever,
            name="HttpPushListener",
            daemon=True,
        )
        self._thread.start()

        with self._lock:
            self._last_request_at = time.monotonic()

        self.logger.info("HTTP push listener started", extra={"host": self.host, "port": self.port})

    def stop(self) -> None:
        if self._httpd:
            self._httpd.shutdown()
            self._httpd.server_close()
            self._httpd = None

        if self._thread:
            self._thread.join(timeout=5.0)
            self._thread = None

    def seconds_since_last_request(self) -> float | None:
        with self._lock:
            if self._last_request_at is None:
                return None
            return time.monotonic() - self._last_request_at

    def _build_handler_class(self):
        listener = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                query = parse_qs(urlparse(self.path).query)
                data: dict[str, str] = {}

                for query_param, field_name in listener.field_map.items():
                    values = query.get(query_param)
                    if values:
                        data[field_name] = values[0]

                with listener._lock:
                    listener._last_request_at = time.monotonic()

                try:
                    listener.on_data(data)
                except Exception:
                    listener.logger.exception("on_data handler raised")

                self.send_response(200)
                self.end_headers()

            def log_message(self, format: str, *args) -> None:
                pass

        return Handler
