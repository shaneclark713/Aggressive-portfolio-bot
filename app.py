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
from brokers.alpaca import AlpacaClient
from brokers.tradier import TradierClient
from brokers.execution_router import ExecutionRouter
from telegram_bot.bot import build_telegram_app
from services.config_service import ConfigService
from services.discovery_service import DiscoveryService
from services.watchlist_service import WatchlistService
from services.alert_service import AlertService
from services.trade_review_service import TradeReviewService
from services.premarket_service import PremarketService
from services.midday_service import MiddayService
from services.postmarket_service import PostmarketService
from services.live_execution_service import LiveExecutionService
from services.options_chain_ingest_service import OptionsChainIngestService
from services.trailing_stop_service import TrailingStopService
from services.position_sync_service import PositionSyncService
from services.broker_ladder_service import BrokerLadderService
from services.risk_service import RiskService
from ledger.sheets_client import GoogleSheetsLedger


async def _close_client(client) -> None:
    if client is None:
        return
    try:
        close = getattr(client, "close", None)
        if close is None:
            return
        result = close()
        if asyncio.iscoroutine(result):
            await result
    except Exception:
        pass


async def _connect_client(client) -> None:
    if client is None:
        return
    try:
        connect = getattr(client, "connect", None)
        if connect is None:
            return
        result = connect()
        if asyncio.iscoroutine(result):
            await result
    except Exception:
        pass


def _has_alpaca_credentials(client: AlpacaClient | None) -> bool:
    return bool(client and getattr(client, "api_key", "") and getattr(client, "secret_key", ""))


def _has_tradier_credentials(client: TradierClient | None) -> bool:
    return bool(client and getattr(client, "token", "") and getattr(client, "account_id", ""))


async def main() -> None:
    settings = load_settings()
    configure_logging(settings.log_level, settings.storage_path)
    run_migrations(settings.storage_path)
    conn = connect_db(settings.storage_path)

    market = None
    news = None
    econ = None
    alpaca_paper = None
    alpaca_live = None
    tradier_paper = None
    tradier_live = None
    telegram_app = None
    scheduler = None

    try:
        trade_repo = TradeRepository(conn)
        alert_repo = AlertRepository(conn)
        execution_log_repo = ExecutionLogRepository(conn)
        settings_repo = SettingsRepository(conn)

        config_service = ConfigService(settings_repo, settings)
        config_service.reset_execution_mode_on_boot()

        market = PolygonMarketDataClient(settings.polygon_api_key)
        news = FinnhubNewsClient(settings.finnhub_api_key)
        econ = FinnhubEconomicCalendarClient(settings.finnhub_api_key)
        await market.connect()
        await news.connect()
        await econ.connect()

        router = StrategyRouter()
        discovery_service = DiscoveryService(market, config_service, settings.storage_path)
        universe_filter = UniverseFilter(market, config_service, discovery_service)
        scanner = ScannerService(market, universe_filter, router, news_client=news, econ_client=econ)

        alpaca_paper = AlpacaClient(
            api_key=getattr(settings, "alpaca_paper_api_key", ""),
            secret_key=getattr(settings, "alpaca_paper_secret_key", ""),
            base_url=getattr(settings, "alpaca_paper_base_url", "https://paper-api.alpaca.markets"),
        )
        alpaca_live = AlpacaClient(
            api_key=getattr(settings, "alpaca_live_api_key", ""),
            secret_key=getattr(settings, "alpaca_live_secret_key", ""),
            base_url=getattr(settings, "alpaca_live_base_url", "https://api.alpaca.markets"),
        )
        tradier_paper = TradierClient(
            token=getattr(settings, "tradier_paper_access_token", ""),
            account_id=getattr(settings, "tradier_paper_account_id", ""),
            base_url=getattr(settings, "tradier_paper_base_url", "https://sandbox.tradier.com/v1"),
        )
        tradier_live = TradierClient(
            token=getattr(settings, "tradier_live_access_token", ""),
            account_id=getattr(settings, "tradier_live_account_id", ""),
            base_url=getattr(settings, "tradier_live_base_url", "https://api.tradier.com/v1"),
        )

        for client in (alpaca_paper, alpaca_live):
            if _has_alpaca_credentials(client):
                await _connect_client(client)

        sheets = GoogleSheetsLedger(
            settings.google_credentials_dict,
            settings.google_spreadsheet_id,
            settings.google_options_worksheet,
            settings.google_futures_worksheet,
            settings.google_monthly_summary_worksheet,
        )
        sheets.connect()

        execution_router = ExecutionRouter(
            alpaca_client=alpaca_live if _has_alpaca_credentials(alpaca_live) else alpaca_paper,
            tradier_client=tradier_live if _has_tradier_credentials(tradier_live) else tradier_paper,
            config_service=config_service,
            alpaca_paper_client=alpaca_paper,
            alpaca_live_client=alpaca_live,
            tradier_paper_client=tradier_paper,
            tradier_live_client=tradier_live,
        )
        trailing_stop_service = TrailingStopService(settings_repo)
        risk_service = RiskService(settings_repo, trade_repo, config_service)
        live_execution_service = LiveExecutionService(
            settings_repo,
            execution_router,
            trailing_stop_service=trailing_stop_service,
            risk_service=risk_service,
        )

        mode_aware_tradier = execution_router.tradier_proxy()
        mode_aware_alpaca = execution_router.alpaca_proxy()
        options_chain_ingest_service = OptionsChainIngestService(settings_repo, mode_aware_tradier)
        position_sync_service = PositionSyncService(
            trailing_stop_service,
            alpaca_client=mode_aware_alpaca,
            tradier_client=mode_aware_tradier,
        )
        broker_ladder_service = BrokerLadderService(execution_router)

        watchlist_service = WatchlistService(universe_filter)
        alert_service = AlertService(
            alert_repo,
            trade_repo,
            execution_log_repo,
            config_service,
            settings,
            execution_router=execution_router,
            risk_service=risk_service,
        )
        trade_review_service = TradeReviewService(trade_repo, settings)

        app_services = {
            "alert_repo": alert_repo,
            "trade_repo": trade_repo,
            "execution_log_repo": execution_log_repo,
            "scanner": scanner,
            "alert_service": alert_service,
            "execution_router": execution_router,
            "discovery_service": discovery_service,
            "universe_filter": universe_filter,
            "tradier_client": mode_aware_tradier,
            "tradier_paper_client": tradier_paper,
            "tradier_live_client": tradier_live,
            "alpaca_client": mode_aware_alpaca,
            "alpaca_paper_client": alpaca_paper,
            "alpaca_live_client": alpaca_live,
            "live_execution_service": live_execution_service,
            "options_chain_ingest_service": options_chain_ingest_service,
            "trailing_stop_service": trailing_stop_service,
            "position_sync_service": position_sync_service,
            "broker_ladder_service": broker_ladder_service,
            "risk_service": risk_service,
        }

        telegram_app = build_telegram_app(
            settings.telegram_bot_token,
            app_services,
            config_service,
            settings.telegram_admin_chat_id,
        )
        telegram_app.bot_data["app_services"] = app_services

        premarket = PremarketService(
            telegram_app,
            settings.telegram_admin_chat_id,
            news,
            econ,
            watchlist_service,
            scanner,
            alert_service,
            config_service,
            alert_repo,
        )
        midday = MiddayService(
            telegram_app,
            settings.telegram_admin_chat_id,
            news,
            None,
            None,
            trade_repo,
            trade_review_service,
        )
        postmarket = PostmarketService(telegram_app, settings.telegram_admin_chat_id, news, trade_repo)

        scheduler = build_scheduler(settings.app_timezone)
        register_jobs(
            scheduler,
            {"premarket": premarket, "midday": midday, "postmarket": postmarket},
            settings.app_timezone,
        )
        scheduler.start()

        await telegram_app.initialize()
        await telegram_app.start()
        await telegram_app.updater.start_polling()

        while True:
            alert_service.expire_alerts()
            await asyncio.sleep(30)
    finally:
        if telegram_app is not None:
            try:
                if getattr(telegram_app, "updater", None) is not None:
                    await telegram_app.updater.stop()
            except Exception:
                pass
            try:
                await telegram_app.stop()
            except Exception:
                pass
            try:
                await telegram_app.shutdown()
            except Exception:
                pass

        if scheduler is not None:
            try:
                scheduler.shutdown(wait=False)
            except Exception:
                pass

        await _close_client(market)
        await _close_client(news)
        await _close_client(econ)
        await _close_client(alpaca_paper)
        await _close_client(alpaca_live)
        await _close_client(tradier_paper)
        await _close_client(tradier_live)
        conn.close()


if __name__ == "__main__":
    asyncio.run(main())
