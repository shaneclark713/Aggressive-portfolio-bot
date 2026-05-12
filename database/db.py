import logging
import sqlite3
from os import PathLike
from pathlib import Path
from typing import Optional, Union

logger = logging.getLogger("aggressive_portfolio_bot.database.db")

DEFAULT_DB_FILENAME = "trading_bot.sqlite3"
PathInput = Optional[Union[str, PathLike[str], Path]]


def resolve_db_file(db_path: PathInput = None) -> Path:
    """Resolve BOT_STORAGE_PATH into the exact SQLite database file.

    Supported values:
    - unset / empty                  -> storage/trading_bot.sqlite3
    - /var/data                      -> /var/data/trading_bot.sqlite3
    - /var/data/bot.db               -> /var/data/bot.db
    - /var/data/trading_bot.sqlite3  -> /var/data/trading_bot.sqlite3

    This matters on Render because only files under the attached disk mount path
    persist across redeploys/restarts.
    """
    if not db_path:
        return Path("storage") / DEFAULT_DB_FILENAME

    raw_path = Path(db_path).expanduser()

    # Existing directories, directory-like paths, and suffix-less paths are treated
    # as storage folders. Paths with a suffix (.db, .sqlite, .sqlite3, etc.) are
    # treated as the actual SQLite database file.
    if raw_path.exists() and raw_path.is_dir():
        return raw_path / DEFAULT_DB_FILENAME
    if str(raw_path).endswith(("/", "\\")):
        return raw_path / DEFAULT_DB_FILENAME
    if raw_path.suffix:
        return raw_path
    return raw_path / DEFAULT_DB_FILENAME


def connect_db(db_path: PathInput = None) -> sqlite3.Connection:
    db_file = resolve_db_file(db_path)
    db_file.parent.mkdir(parents=True, exist_ok=True)

    logger.info("Using SQLite database at %s", db_file.as_posix())
    conn = sqlite3.connect(db_file.as_posix(), check_same_thread=False)
    conn.row_factory = sqlite3.Row

    # Better durability for small bot settings/trade-state writes.
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _add_column_if_missing(cursor: sqlite3.Cursor, table_name: str, column_name: str, column_definition: str) -> None:
    cursor.execute(f"PRAGMA table_info({table_name})")
    existing_columns = {row[1] for row in cursor.fetchall()}
    if column_name not in existing_columns:
        cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}")


def init_db(db_path: PathInput = None) -> None:
    conn = connect_db(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS active_trades (
            trade_id INTEGER PRIMARY KEY AUTOINCREMENT,
            broker_order_id TEXT,
            symbol TEXT NOT NULL,
            side TEXT NOT NULL,
            strategy TEXT,
            horizon TEXT,
            status TEXT NOT NULL DEFAULT 'OPEN',
            entry_time TEXT,
            exit_time TEXT,
            entry_price REAL,
            exit_price REAL,
            stop_loss REAL,
            take_profit REAL,
            pnl REAL,
            rr_ratio REAL,
            close_reason TEXT,
            entry_snapshot_path TEXT,
            close_snapshot_path TEXT,
            notes TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS trade_audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trade_id INTEGER,
            event_type TEXT NOT NULL,
            event_time TEXT NOT NULL,
            payload TEXT,
            FOREIGN KEY(trade_id) REFERENCES active_trades(trade_id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            alert_id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            strategy TEXT,
            side TEXT,
            payload TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'PENDING',
            created_at TEXT NOT NULL,
            responded_at TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS strategy_states (
            strategy_name TEXT PRIMARY KEY,
            is_enabled INTEGER NOT NULL DEFAULT 1
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS filter_overrides (
            override_key TEXT PRIMARY KEY,
            override_value TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS spy_scan_journal (
            scan_id INTEGER PRIMARY KEY AUTOINCREMENT,
            scan_type TEXT NOT NULL,
            created_at TEXT NOT NULL,
            symbol TEXT NOT NULL DEFAULT 'SPY',
            latest REAL,
            structure_bias TEXT,
            structure_score INTEGER,
            confidence_grade TEXT,
            confidence_score INTEGER,
            trend_probability INTEGER,
            mean_reversion_probability INTEGER,
            dealer_regime TEXT,
            dealer_exposure_score INTEGER,
            payload TEXT NOT NULL
        )
    """)

    _add_column_if_missing(cursor, "spy_scan_journal", "outcome", "TEXT")
    _add_column_if_missing(cursor, "spy_scan_journal", "outcome_notes", "TEXT")
    _add_column_if_missing(cursor, "spy_scan_journal", "outcome_marked_at", "TEXT")

    conn.commit()
    conn.close()
