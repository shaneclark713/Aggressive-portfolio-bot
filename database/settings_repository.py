import json
from typing import Any, Dict, Optional


class SettingsRepository:
    def __init__(self, conn):
        self.conn = conn
        self._ensure_tables()

    def _ensure_tables(self) -> None:
        cursor = self.conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS strategy_states (
                strategy_name TEXT PRIMARY KEY,
                is_enabled INTEGER NOT NULL DEFAULT 1
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS filter_overrides (
                override_key TEXT PRIMARY KEY,
                override_value TEXT NOT NULL
            )
            """
        )

        self.conn.commit()

    def get(self, key: str, default: Optional[Any] = None) -> Any:
        cursor = self.conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = cursor.fetchone()
        if not row:
            return default

        value = row["value"] if hasattr(row, "__getitem__") else row[0]

        try:
            return json.loads(value)
        except Exception:
            return value

    def set(self, key: str, value: Any) -> None:
        serialized = json.dumps(value) if not isinstance(value, str) else value
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO settings (key, value)
            VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (key, serialized),
        )
        self.conn.commit()

    def delete(self, key: str) -> None:
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM settings WHERE key = ?", (key,))
        self.conn.commit()

    def get_active_preset(self) -> str:
        return self.get("active_preset", "day_trade_momentum")

    def set_active_preset(self, preset_name: str) -> None:
        self.set("active_preset", preset_name)

    def get_execution_mode(self) -> str:
        return self.get("execution_mode", "alerts_only")

    def set_execution_mode(self, mode: str) -> None:
        self.set("execution_mode", mode)

    def get_strategy_states(self) -> Dict[str, bool]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT strategy_name, is_enabled FROM strategy_states")
        rows = cursor.fetchall()
        return {
            (row["strategy_name"] if hasattr(row, "__getitem__") else row[0]): bool(
                row["is_enabled"] if hasattr(row, "__getitem__") else row[1]
            )
            for row in rows
        }

    def set_strategy_state(self, strategy_name: str, is_enabled: bool) -> None:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO strategy_states (strategy_name, is_enabled)
            VALUES (?, ?)
            ON CONFLICT(strategy_name) DO UPDATE SET is_enabled = excluded.is_enabled
            """,
            (strategy_name, 1 if is_enabled else 0),
        )
        self.conn.commit()

    def get_filter_overrides(self) -> Dict[str, Any]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT override_key, override_value FROM filter_overrides")
        rows = cursor.fetchall()

        result: Dict[str, Any] = {}
        for row in rows:
            key = row["override_key"] if hasattr(row, "__getitem__") else row[0]
            value = row["override_value"] if hasattr(row, "__getitem__") else row[1]
            try:
                result[key] = json.loads(value)
            except Exception:
                result[key] = value
        return result

    def set_filter_override(self, override_key: str, override_value: Any) -> None:
        serialized = (
            json.dumps(override_value)
            if not isinstance(override_value, str)
            else override_value
        )
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO filter_overrides (override_key, override_value)
            VALUES (?, ?)
            ON CONFLICT(override_key) DO UPDATE SET override_value = excluded.override_value
            """,
            (override_key, serialized),
        )
        self.conn.commit()

    def clear_filter_override(self, override_key: str) -> None:
        cursor = self.conn.cursor()
        cursor.execute(
            "DELETE FROM filter_overrides WHERE override_key = ?",
            (override_key,),
        )
        self.conn.commit()
