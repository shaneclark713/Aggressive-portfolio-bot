from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Union


def _resolve_storage_root(storage_path: Union[str, Path, None]) -> Path:
    """Return a directory that can safely hold logs.

    BOT_STORAGE_PATH may be either a directory, such as:
        /var/data

    or a SQLite database file, such as:
        /var/data/bot.db

    Logging should create folders under the parent directory when a file path is
    provided. It must never try to mkdir() the database file itself.
    """
    if not storage_path:
        return Path("storage")

    path = Path(storage_path)

    # Treat common database/file suffixes as files. This covers /var/data/bot.db
    # and /var/data/trading_bot.sqlite3 while keeping /var/data as a directory.
    if path.suffix:
        return path.parent

    return path


def configure_logging(level: str = "INFO", storage_path: Union[str, Path, None] = None) -> None:
    storage_root = _resolve_storage_root(storage_path)
    storage_root.mkdir(parents=True, exist_ok=True)

    log_dir = storage_root / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "bot.log"

    numeric_level = getattr(logging, str(level or "INFO").upper(), logging.INFO)
    log_format = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"

    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Avoid duplicate handlers after reloads/tests.
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)
        try:
            handler.close()
        except Exception:
            pass

    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(numeric_level)
    stream_handler.setFormatter(logging.Formatter(log_format))

    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=5_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setLevel(numeric_level)
    file_handler.setFormatter(logging.Formatter(log_format))

    root_logger.addHandler(stream_handler)
    root_logger.addHandler(file_handler)

    logging.getLogger("aggressive_portfolio_bot.config.logging").info(
        "Logging configured. storage_root=%s log_file=%s",
        storage_root,
        log_file,
    )
