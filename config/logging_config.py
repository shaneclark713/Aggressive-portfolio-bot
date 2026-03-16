import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


def configure_logging(level: str, storage_path: Path) -> None:
    storage_path.mkdir(parents=True, exist_ok=True)
    log_dir = storage_path / 'logs'
    log_dir.mkdir(parents=True, exist_ok=True)
    handlers = [logging.StreamHandler(), RotatingFileHandler(log_dir / 'bot.log', maxBytes=2_000_000, backupCount=5)]
    logging.basicConfig(level=getattr(logging, level.upper(), logging.INFO), format='%(asctime)s | %(levelname)s | %(name)s | %(message)s', handlers=handlers, force=True)
