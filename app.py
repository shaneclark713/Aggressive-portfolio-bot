from __future__ import annotations
import asyncio
from config.settings import load_settings
from config.logging_config import configure_logging
from core.scheduler import build_scheduler, register_jobs
from database.db import connect_db
from database.migrations import run_migrations
from database.repositories import TradeRepository, AlertRepository, ExecutionLogRepository
from database.settings_repository import SettingsRepository
from data.market_data import PolygonMarketDataClient
from data.news_data import FinnhubNewsClient
from data.econ_calendar import FinnhubEconomicCalendarClient
from data.universe_filter import UniverseFilter
from data.scanners import ScannerService
from strategies.router import StrategyRouter
from brokers.ibkr import IBKRClient
from brokers.tradovate import TradovateClient
from brokers.execution_router import ExecutionRouter
from telegram_bot.bot import build_telegram_app
from services.config_service import ConfigService
from services.watchlist_service import WatchlistService
from services.alert_service import AlertService
from services.trade_review_service import TradeReviewService
from services.premarket_service import PremarketService
from services.midday_service import MiddayService
from services.postmarket_service import PostmarketService
from ledger.sheets_client import GoogleSheetsLedger

async def main():
    settings=load_settings(); configure_logging(settings.log_level, settings.storage_path)
    conn=connect_db(settings.storage_path); run_migrations(conn)
    trade_repo=TradeRepository(conn); alert_repo=AlertRepository(conn); execution_log_repo=ExecutionLogRepository(conn); settings_repo=SettingsRepository(conn)
    config_service=ConfigService(settings_repo, settings); config_service.reset_execution_mode_on_boot()
    market=PolygonMarketDataClient(settings.polygon_api_key); news=FinnhubNewsClient(settings.finnhub_api_key); econ=FinnhubEconomicCalendarClient(settings.finnhub_api_key)
    await market.connect(); await news.connect(); await econ.connect()
    router=StrategyRouter(config_service.get_strategy_states()); universe_filter=UniverseFilter(market); scanner=ScannerService(market, universe_filter, router)
    ibkr=IBKRClient(settings.ibkr_host, settings.ibkr_port, settings.ibkr_client_id, settings.ibkr_account_id); tradovate=TradovateClient(settings.tradovate_base_url, settings.tradovate_ws_url, settings.tradovate_username, settings.tradovate_password, settings.tradovate_cid, settings.tradovate_secret, settings.tradovate_app_id, settings.tradovate_app_version, settings.tradovate_device_id, settings.tradovate_account_id)
    try:
        await ibkr.connect()
    except Exception: pass
    try:
        await tradovate.connect()
    except Exception: pass
    sheets=GoogleSheetsLedger(settings.google_credentials_dict, settings.google_spreadsheet_id, settings.google_options_worksheet, settings.google_futures_worksheet, settings.google_monthly_summary_worksheet); sheets.connect()
    watchlist_service=WatchlistService(universe_filter); alert_service=AlertService(alert_repo, trade_repo, execution_log_repo, config_service, settings); trade_review_service=TradeReviewService(trade_repo, settings)
    app_services={'alert_repo':alert_repo,'trade_repo':trade_repo,'execution_log_repo':execution_log_repo}
    telegram_app=build_telegram_app(settings.telegram_bot_token, app_services, config_service, settings.telegram_admin_chat_id)
    premarket=PremarketService(telegram_app, settings.telegram_admin_chat_id, news, econ, watchlist_service, scanner, alert_service, config_service, alert_repo)
    midday=MiddayService(telegram_app, settings.telegram_admin_chat_id, news, ibkr, tradovate, trade_repo, trade_review_service)
    postmarket=PostmarketService(telegram_app, settings.telegram_admin_chat_id, news, trade_repo)
    scheduler=build_scheduler(settings.app_timezone); register_jobs(scheduler, {'premarket':premarket,'midday':midday,'postmarket':postmarket}, settings.app_timezone); scheduler.start(); await telegram_app.initialize(); await telegram_app.start(); await telegram_app.updater.start_polling();
    try:
        while True:
            alert_service.expire_alerts(); await asyncio.sleep(30)
    finally:
        await telegram_app.updater.stop(); await telegram_app.stop(); await telegram_app.shutdown(); scheduler.shutdown(wait=False); await market.close(); await news.close(); await econ.close(); await ibkr.close(); await tradovate.close(); conn.close()

if __name__=='__main__': asyncio.run(main())
