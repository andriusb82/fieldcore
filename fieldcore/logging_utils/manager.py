import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


class LoggingManager:
    _initialized = False

    @classmethod
    def setup(
        cls,
        log_file: str = "logs/app.log",
        level: str = "INFO",
        max_bytes: int = 5_000_000,
        backup_count: int = 5,
    ) -> None:
        if cls._initialized:
            return

        Path(log_file).parent.mkdir(parents=True, exist_ok=True)

        root_logger = logging.getLogger()
        root_logger.setLevel(level)

        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        )

        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)

        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)

        cls._initialized = True


def setup_logging(
    log_file: str = "logs/app.log",
    level: str = "INFO",
    max_bytes: int = 5_000_000,
    backup_count: int = 5,
) -> None:
    LoggingManager.setup(
        log_file=log_file,
        level=level,
        max_bytes=max_bytes,
        backup_count=backup_count,
    )


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
