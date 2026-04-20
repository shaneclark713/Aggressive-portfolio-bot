from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class Settings:
    app_env: str
    app_timezone: str
    log_level: str

    telegram_bot_token: str
    telegram_admin_chat_id: int

    polygon_api_key: str
    finnhub_api_key: str

    alpaca_api_key: str
    alpaca_secret_key: str
    alpaca_base_url: str

    tradier_access_token: str
    tradier_account_id: str
    tradier_base_url: str

    google_sheets_credentials_json: str
    google_spreadsheet_id: str
    google_options_worksheet: str
    google_futures_worksheet: str
    google_monthly_summary_worksheet: str

    bot_default_execution_mode: str
    bot_max_risk_per_trade_pct: float
    bot_max_daily_risk_pct: float
    bot_approval_timeout_seconds: int
    bot_day_trade_auto_close_time_ny: str
    bot_enable_screenshots: bool
    bot_storage_path: str

    broker_enabled: bool
    enable_alpaca: bool
    enable_tradier: bool

    @property
    def storage_path(self) -> Path:
        return Path(self.bot_storage_path)

    @property
    def google_credentials_dict(self) -> dict:
        if not self.google_sheets_credentials_json.strip():
            return {}
        return json.loads(self.google_sheets_credentials_json)


def _get(name: str, default: str = "") -> str:
    return os.getenv(name, default)


def _get_bool(name: str, default: str = "false") -> bool:
    return _get(name, default).strip().lower() in {"1", "true", "yes", "on"}


def load_settings() -> Settings:
    return Settings(
        app_env=_get("APP_ENV", "production"),
        app_timezone=_get("APP_TIMEZONE", "America/Phoenix"),
        log_level=_get("LOG_LEVEL", "INFO"),

        telegram_bot_token=_get("TELEGRAM_BOT_TOKEN", ""),
        telegram_admin_chat_id=int(_get("TELEGRAM_ADMIN_CHAT_ID", "0") or 0),

        polygon_api_key=_get("POLYGON_API_KEY", ""),
        finnhub_api_key=_get("FINNHUB_API_KEY", ""),

        alpaca_api_key=_get("ALPACA_API_KEY", ""),
        alpaca_secret_key=_get("ALPACA_SECRET_KEY", ""),
        alpaca_base_url=_get("ALPACA_BASE_URL", "https://paper-api.alpaca.markets"),

        tradier_access_token=_get("TRADIER_ACCESS_TOKEN", ""),
        tradier_account_id=_get("TRADIER_ACCOUNT_ID", ""),
        tradier_base_url=_get("TRADIER_BASE_URL", "https://api.tradier.com/v1"),

        google_sheets_credentials_json=_get("GOOGLE_SHEETS_CREDENTIALS_JSON", ""),
        google_spreadsheet_id=_get("GOOGLE_SPREADSHEET_ID", ""),
        google_options_worksheet=_get("GOOGLE_OPTIONS_WORKSHEET", "Options_Ledger"),
        google_futures_worksheet=_get("GOOGLE_FUTURES_WORKSHEET", "Futures_Ledger"),
        google_monthly_summary_worksheet=_get("GOOGLE_MONTHLY_SUMMARY_WORKSHEET", "Monthly_Summary"),

        bot_default_execution_mode=_get("BOT_DEFAULT_EXECUTION_MODE", "alerts_only"),
        bot_max_risk_per_trade_pct=float(_get("BOT_MAX_RISK_PER_TRADE_PCT", "0.75")),
        bot_max_daily_risk_pct=float(_get("BOT_MAX_DAILY_RISK_PCT", "4.0")),
        bot_approval_timeout_seconds=int(_get("BOT_APPROVAL_TIMEOUT_SECONDS", "180")),
        bot_day_trade_auto_close_time_ny=_get("BOT_DAY_TRADE_AUTO_CLOSE_TIME_NY", "15:45"),
        bot_enable_screenshots=_get_bool("BOT_ENABLE_SCREENSHOTS", "true"),
        bot_storage_path=_get("BOT_STORAGE_PATH", "storage"),

        broker_enabled=_get_bool("BROKER_ENABLED", "true"),
        enable_alpaca=_get_bool("ENABLE_ALPACA", "true"),
        enable_tradier=_get_bool("ENABLE_TRADIER", "false"),
    )
