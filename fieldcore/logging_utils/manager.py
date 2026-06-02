import json
import logging
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Mapping


DEFAULT_LOGGING_CONFIG: dict[str, Any] = {
    "log_file": "logs/app.log",
    "level": "INFO",
    "max_bytes": 5_000_000,
    "backup_count": 5,
    "format": "text",
    "console": True,
    "module_levels": {},
}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_record = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "message": record.getMessage(),
        }

        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)

        for key, value in record.__dict__.items():
            if key.startswith("_") or key in _STANDARD_LOG_RECORD_FIELDS:
                continue
            log_record[key] = value

        return json.dumps(log_record, ensure_ascii=False, default=str)


_STANDARD_LOG_RECORD_FIELDS = {
    "args",
    "asctime",
    "created",
    "exc_info",
    "exc_text",
    "filename",
    "funcName",
    "levelname",
    "levelno",
    "lineno",
    "module",
    "msecs",
    "message",
    "msg",
    "name",
    "pathname",
    "process",
    "processName",
    "relativeCreated",
    "stack_info",
    "thread",
    "threadName",
}


class LoggingManager:
    _initialized = False

    @classmethod
    def setup(
        cls,
        log_file: str = "logs/app.log",
        level: str = "INFO",
        max_bytes: int = 5_000_000,
        backup_count: int = 5,
        log_format: str = "text",
        console: bool = True,
        module_levels: Mapping[str, str] | None = None,
        force: bool = False,
    ) -> None:
        if cls._initialized and not force:
            cls.apply_module_levels(module_levels or {})
            return

        Path(log_file).parent.mkdir(parents=True, exist_ok=True)

        root_logger = logging.getLogger()
        root_logger.setLevel(_parse_log_level(level))

        if force:
            for handler in root_logger.handlers[:]:
                root_logger.removeHandler(handler)
                handler.close()

        if not root_logger.handlers:
            formatter = cls._create_formatter(log_format)

            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=max_bytes,
                backupCount=backup_count,
                encoding="utf-8",
            )
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)

            if console:
                console_handler = logging.StreamHandler()
                console_handler.setFormatter(formatter)
                root_logger.addHandler(console_handler)

        cls.apply_module_levels(module_levels or {})
        cls._initialized = True

    @classmethod
    def setup_from_config(
        cls,
        config: Mapping[str, Any],
        section: str = "logging",
        force: bool = False,
    ) -> None:
        logging_config = _extract_logging_config(config, section)
        merged_config = {**DEFAULT_LOGGING_CONFIG, **logging_config}

        cls.setup(
            log_file=str(merged_config["log_file"]),
            level=str(merged_config["level"]),
            max_bytes=int(merged_config["max_bytes"]),
            backup_count=int(merged_config["backup_count"]),
            log_format=str(merged_config["format"]),
            console=bool(merged_config["console"]),
            module_levels=merged_config.get("module_levels") or {},
            force=force,
        )

    @classmethod
    def apply_module_levels(cls, module_levels: Mapping[str, str]) -> None:
        for module_name, module_level in module_levels.items():
            logging.getLogger(module_name).setLevel(_parse_log_level(module_level))

    @staticmethod
    def _create_formatter(log_format: str) -> logging.Formatter:
        if log_format.lower() == "json":
            return JsonFormatter()

        return logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        )


def setup_logging(
    log_file: str = "logs/app.log",
    level: str = "INFO",
    max_bytes: int = 5_000_000,
    backup_count: int = 5,
    log_format: str = "text",
    console: bool = True,
    module_levels: Mapping[str, str] | None = None,
    force: bool = False,
) -> None:
    LoggingManager.setup(
        log_file=log_file,
        level=level,
        max_bytes=max_bytes,
        backup_count=backup_count,
        log_format=log_format,
        console=console,
        module_levels=module_levels,
        force=force,
    )


def setup_logging_from_config(
    config: Mapping[str, Any],
    section: str = "logging",
    force: bool = False,
) -> None:
    LoggingManager.setup_from_config(config=config, section=section, force=force)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def _extract_logging_config(config: Mapping[str, Any], section: str) -> Mapping[str, Any]:
    if section in config and isinstance(config[section], Mapping):
        return config[section]
    return config


def _parse_log_level(level: str | int) -> int:
    if isinstance(level, int):
        return level

    parsed_level = logging.getLevelName(level.upper())
    if isinstance(parsed_level, int):
        return parsed_level

    raise ValueError(f"Unsupported log level: {level}")
