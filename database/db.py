import sqlite3
from pathlib import Path

DEFAULT_DB_PATH = "database/trading_bot.sqlite3"


def connect_db(db_path: str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    db_file = Path(db_path)
    db_file.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_file.as_posix(), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str = DEFAULT_DB_PATH) -> None:
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

    conn.commit()
    conn.close()
