import logging
from pathlib import Path


def configure_logging(log_level: str = "INFO", storage_path: str = "storage") -> None:
    storage_dir = Path(storage_path)
    storage_dir.mkdir(parents=True, exist_ok=True)

    log_dir = storage_dir / "logs"

    if log_dir.exists() and not log_dir.is_dir():
        log_dir.unlink()

    log_dir.mkdir(parents=True, exist_ok=True)

    log_file = log_dir / "bot.log"

    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )

    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(formatter)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)

    root_logger.addHandler(file_handler)
    root_logger.addHandler(stream_handler)
