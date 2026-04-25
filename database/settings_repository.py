import json
from copy import deepcopy
from typing import Any, Dict, Optional


class SettingsRepository:
    DEFAULT_DAY_TRADE_EXECUTION = {
        "risk_pct": 0.01,
        "atr_multiplier": 1.0,
        "position_mode": "auto",
        "take_profit_pct": 0.20,
        "stop_loss_pct": 0.08,
        "max_concurrent_positions": 3,
        "time_of_day_restrictor": "15:00",
        "max_spread_pct": 0.03,
        "min_volume": 500_000,
        "max_slippage_pct": 0.02,
        "ladder_steps": 3,
        "ladder_spacing_pct": 0.01,
        "trail_type": "percent",
        "trail_value": 0.02,
        "max_consecutive_losses": 3,
    }

    DEFAULT_SWING_TRADE_EXECUTION = {
        "risk_pct": 0.01,
        "atr_multiplier": 1.5,
        "position_mode": "auto",
        "take_profit_pct": 0.35,
        "stop_loss_pct": 0.12,
        "max_concurrent_positions": 5,
        "time_of_day_restrictor": "15:30",
        "max_spread_pct": 0.05,
        "min_volume": 250_000,
        "max_slippage_pct": 0.03,
        "ladder_steps": 2,
        "ladder_spacing_pct": 0.02,
        "trail_type": "percent",
        "trail_value": 0.04,
        "max_consecutive_losses": 3,
    }

    DEFAULT_OPTIONS_EXECUTION = {
        **DEFAULT_DAY_TRADE_EXECUTION,
        "position_mode": "options",
        "max_concurrent_positions": 3,
        "time_of_day_restrictor": "15:00",
        "max_consecutive_losses": 3,
    }

    DEFAULT_OPTIONS_SETTINGS = {
        "enabled": False,
        "delta_min": 0.30,
        "delta_max": 0.70,
        "min_open_interest": 1000,
        "contract_min_price": 0.50,
        "contract_max_price": 8.00,
        "min_daily_volume": 100,
        "expiry_mode": "weekly",
        "expiry_count": 1,
        "chain_symbol": "SPY",
    }

    EXECUTION_SCOPE_ALIASES = {
        "day": "day_trade",
        "day_trade": "day_trade",
        "daytrade": "day_trade",
        "intraday": "day_trade",
        "swing": "swing_trade",
        "swing_trade": "swing_trade",
        "swingtrade": "swing_trade",
        "overnight": "swing_trade",
        "option": "options",
        "options": "options",
        "option_trade": "options",
        "options_trade": "options",
    }

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

    def normalize_execution_scope(self, scope: str | None) -> str:
        raw = str(scope or "day_trade").strip().lower()
        return self.EXECUTION_SCOPE_ALIASES.get(raw, "day_trade")

    def _execution_defaults(self, scope: str) -> Dict[str, Any]:
        normalized = self.normalize_execution_scope(scope)
        if normalized == "swing_trade":
            return deepcopy(self.DEFAULT_SWING_TRADE_EXECUTION)
        if normalized == "options":
            return deepcopy(self.DEFAULT_OPTIONS_EXECUTION)
        return deepcopy(self.DEFAULT_DAY_TRADE_EXECUTION)

    def get_execution_settings(self, scope: str | None = None) -> Dict[str, Any]:
        if scope is None:
            return {
                "day_trade": self.get_execution_settings("day_trade"),
                "swing_trade": self.get_execution_settings("swing_trade"),
                "options": self.get_execution_settings("options"),
            }

        normalized_scope = self.normalize_execution_scope(scope)
        defaults = self._execution_defaults(normalized_scope)

        legacy = self.get("execution_settings", {}) or {}
        stored = self.get(f"execution_settings.{normalized_scope}", {}) or {}

        merged = defaults
        if isinstance(legacy, dict):
            merged.update(legacy)
        if isinstance(stored, dict):
            merged.update(stored)
        return merged

    def set_execution_settings(self, scope: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        normalized_scope = self.normalize_execution_scope(scope)
        merged = self._execution_defaults(normalized_scope)
        merged.update(payload or {})
        self.set(f"execution_settings.{normalized_scope}", merged)
        return merged

    def update_execution_settings(self, scope: str, **updates: Any) -> Dict[str, Any]:
        current = self.get_execution_settings(scope)
        current.update(updates)
        return self.set_execution_settings(scope, current)

    def get_options_settings(self) -> Dict[str, Any]:
        legacy = self.get("options_settings", {}) or {}
        merged = deepcopy(self.DEFAULT_OPTIONS_SETTINGS)
        if isinstance(legacy, dict):
            merged.update(legacy)

        expiry_pref = str(merged.pop("expiry_preference", merged.get("expiry_mode", "weekly")) or "weekly").strip().lower()
        expiry_count = merged.get("expiry_count", 1)
        if expiry_pref == "nearest":
            expiry_pref = "0dte"
            expiry_count = 0
        if expiry_pref == "any":
            expiry_pref = "weekly"
        merged["expiry_mode"] = expiry_pref
        merged["expiry_count"] = int(expiry_count or 0)
        return merged

    def set_options_settings(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        merged = deepcopy(self.DEFAULT_OPTIONS_SETTINGS)
        merged.update(payload or {})
        if str(merged.get("expiry_mode", "")).lower() == "nearest":
            merged["expiry_mode"] = "0dte"
            merged["expiry_count"] = 0
        self.set("options_settings", merged)
        return merged

    def update_options_settings(self, **updates: Any) -> Dict[str, Any]:
        current = self.get_options_settings()
        current.update(updates)
        return self.set_options_settings(current)

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
