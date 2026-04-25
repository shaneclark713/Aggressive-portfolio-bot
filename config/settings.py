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
    ibkr_host: str
    ibkr_port: int
    ibkr_client_id: int
    ibkr_account_id: str
    ibkr_trading_mode: str
    tradovate_env: str
    tradovate_base_url: str
    tradovate_ws_url: str
    tradovate_username: str
    tradovate_password: str
    tradovate_cid: str
    tradovate_secret: str
    tradovate_app_id: str
    tradovate_app_version: str
    tradovate_device_id: str
    tradovate_account_id: str
    polygon_api_key: str
    finnhub_api_key: str
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
    enable_ibkr: bool
    enable_tradovate: bool

    # Legacy single-client broker variables. These are kept so old deployments do not break.
    alpaca_api_key: str
    alpaca_secret_key: str
    alpaca_base_url: str
    tradier_access_token: str
    tradier_account_id: str
    tradier_base_url: str

    # Mode-aware broker variables. Telegram Mode uses these directly:
    # alerts_only -> no order submission
    # paper       -> paper/sandbox clients
    # live        -> live/production clients
    alpaca_paper_api_key: str
    alpaca_paper_secret_key: str
    alpaca_paper_base_url: str
    alpaca_live_api_key: str
    alpaca_live_secret_key: str
    alpaca_live_base_url: str
    tradier_paper_access_token: str
    tradier_paper_account_id: str
    tradier_paper_base_url: str
    tradier_live_access_token: str
    tradier_live_account_id: str
    tradier_live_base_url: str

    @property
    def storage_path(self) -> Path:
        return Path(self.bot_storage_path)

    @property
    def google_credentials_dict(self) -> dict:
        if not self.google_sheets_credentials_json.strip():
            return {}
        return json.loads(self.google_sheets_credentials_json)


def _get(name: str, default: str = '') -> str:
    return os.getenv(name, default)


def _get_bool(name: str, default: str = 'false') -> bool:
    return _get(name, default).strip().lower() in {'1', 'true', 'yes', 'on'}


def _first(*values: str) -> str:
    for value in values:
        if str(value or '').strip():
            return value
    return ''


def load_settings() -> Settings:
    legacy_alpaca_base = _get('ALPACA_BASE_URL', 'https://paper-api.alpaca.markets')
    legacy_tradier_base = _get('TRADIER_BASE_URL', 'https://api.tradier.com/v1')

    alpaca_paper_api_key = _first(_get('ALPACA_PAPER_API_KEY'), _get('ALPACA_API_KEY'))
    alpaca_paper_secret_key = _first(_get('ALPACA_PAPER_SECRET_KEY'), _get('ALPACA_SECRET_KEY'))
    alpaca_live_api_key = _first(_get('ALPACA_LIVE_API_KEY'), _get('ALPACA_API_KEY') if 'paper-api' not in legacy_alpaca_base else '')
    alpaca_live_secret_key = _first(_get('ALPACA_LIVE_SECRET_KEY'), _get('ALPACA_SECRET_KEY') if 'paper-api' not in legacy_alpaca_base else '')

    tradier_paper_access_token = _first(_get('TRADIER_PAPER_ACCESS_TOKEN'), _get('TRADIER_ACCESS_TOKEN') if 'sandbox' in legacy_tradier_base else '')
    tradier_paper_account_id = _first(_get('TRADIER_PAPER_ACCOUNT_ID'), _get('TRADIER_ACCOUNT_ID') if 'sandbox' in legacy_tradier_base else '')
    tradier_live_access_token = _first(_get('TRADIER_LIVE_ACCESS_TOKEN'), _get('TRADIER_ACCESS_TOKEN') if 'sandbox' not in legacy_tradier_base else '')
    tradier_live_account_id = _first(_get('TRADIER_LIVE_ACCOUNT_ID'), _get('TRADIER_ACCOUNT_ID') if 'sandbox' not in legacy_tradier_base else '')

    return Settings(
        app_env=_get('APP_ENV', 'production'),
        app_timezone=_get('APP_TIMEZONE', 'America/Phoenix'),
        log_level=_get('LOG_LEVEL', 'INFO'),
        telegram_bot_token=_get('TELEGRAM_BOT_TOKEN', ''),
        telegram_admin_chat_id=int(_get('TELEGRAM_ADMIN_CHAT_ID', '0') or 0),
        ibkr_host=_get('IBKR_HOST', '127.0.0.1'),
        ibkr_port=int(_get('IBKR_PORT', '7497')),
        ibkr_client_id=int(_get('IBKR_CLIENT_ID', '10')),
        ibkr_account_id=_get('IBKR_ACCOUNT_ID', ''),
        ibkr_trading_mode=_get('IBKR_TRADING_MODE', 'paper'),
        tradovate_env=_get('TRADOVATE_ENV', 'demo'),
        tradovate_base_url=_get('TRADOVATE_BASE_URL', 'https://demo.tradovateapi.com/v1'),
        tradovate_ws_url=_get('TRADOVATE_WS_URL', 'wss://demo.tradovateapi.com/v1/websocket'),
        tradovate_username=_get('TRADOVATE_USERNAME', ''),
        tradovate_password=_get('TRADOVATE_PASSWORD', ''),
        tradovate_cid=_get('TRADOVATE_CID', ''),
        tradovate_secret=_get('TRADOVATE_SECRET', ''),
        tradovate_app_id=_get('TRADOVATE_APP_ID', 'AggressivePortfolioBot'),
        tradovate_app_version=_get('TRADOVATE_APP_VERSION', '1.0'),
        tradovate_device_id=_get('TRADOVATE_DEVICE_ID', 'render-bot'),
        tradovate_account_id=_get('TRADOVATE_ACCOUNT_ID', ''),
        polygon_api_key=_get('POLYGON_API_KEY', ''),
        finnhub_api_key=_get('FINNHUB_API_KEY', ''),
        google_sheets_credentials_json=_get('GOOGLE_SHEETS_CREDENTIALS_JSON', ''),
        google_spreadsheet_id=_get('GOOGLE_SPREADSHEET_ID', ''),
        google_options_worksheet=_get('GOOGLE_OPTIONS_WORKSHEET', 'Options_Ledger'),
        google_futures_worksheet=_get('GOOGLE_FUTURES_WORKSHEET', 'Futures_Ledger'),
        google_monthly_summary_worksheet=_get('GOOGLE_MONTHLY_SUMMARY_WORKSHEET', 'Monthly_Summary'),
        bot_default_execution_mode=_get('BOT_DEFAULT_EXECUTION_MODE', 'alerts_only'),
        bot_max_risk_per_trade_pct=float(_get('BOT_MAX_RISK_PER_TRADE_PCT', '0.75')),
        bot_max_daily_risk_pct=float(_get('BOT_MAX_DAILY_RISK_PCT', '4.0')),
        bot_approval_timeout_seconds=int(_get('BOT_APPROVAL_TIMEOUT_SECONDS', '180')),
        bot_day_trade_auto_close_time_ny=_get('BOT_DAY_TRADE_AUTO_CLOSE_TIME_NY', '15:45'),
        bot_enable_screenshots=_get_bool('BOT_ENABLE_SCREENSHOTS', 'true'),
        bot_storage_path=_get('BOT_STORAGE_PATH', 'storage'),
        broker_enabled=_get_bool('BROKER_ENABLED', 'false'),
        enable_ibkr=_get_bool('ENABLE_IBKR', 'false'),
        enable_tradovate=_get_bool('ENABLE_TRADOVATE', 'false'),
        alpaca_api_key=_get('ALPACA_API_KEY', ''),
        alpaca_secret_key=_get('ALPACA_SECRET_KEY', ''),
        alpaca_base_url=legacy_alpaca_base,
        tradier_access_token=_get('TRADIER_ACCESS_TOKEN', ''),
        tradier_account_id=_get('TRADIER_ACCOUNT_ID', ''),
        tradier_base_url=legacy_tradier_base,
        alpaca_paper_api_key=alpaca_paper_api_key,
        alpaca_paper_secret_key=alpaca_paper_secret_key,
        alpaca_paper_base_url=_get('ALPACA_PAPER_BASE_URL', 'https://paper-api.alpaca.markets'),
        alpaca_live_api_key=alpaca_live_api_key,
        alpaca_live_secret_key=alpaca_live_secret_key,
        alpaca_live_base_url=_get('ALPACA_LIVE_BASE_URL', 'https://api.alpaca.markets'),
        tradier_paper_access_token=tradier_paper_access_token,
        tradier_paper_account_id=tradier_paper_account_id,
        tradier_paper_base_url=_get('TRADIER_PAPER_BASE_URL', 'https://sandbox.tradier.com/v1'),
        tradier_live_access_token=tradier_live_access_token,
        tradier_live_account_id=tradier_live_account_id,
        tradier_live_base_url=_get('TRADIER_LIVE_BASE_URL', 'https://api.tradier.com/v1'),
    )
