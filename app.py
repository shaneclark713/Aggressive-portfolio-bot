from __future__ import annotations

import asyncio
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from brokers.execution_router import ExecutionRouter
from brokers.ibkr import IBKRClient
from brokers.tradovate import TradovateClient
from config.settings import load_settings
from repositories.market_data import MarketDataRepository
from repositories.settings_repo import SettingsRepository
from repositories.trade_repo import TradeRepository
from services.midday_service import MiddayService
from services.postmarket_service import PostmarketService
from services.premarket_service import PremarketService
from services.scanner import ScannerService
from telegram_bot.bot import build_telegram_app


async def main():
    settings = load_settings()

    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    settings.storage_path.mkdir(parents=True, exist_ok=True)

    settings_repo = SettingsRepository(settings.storage_path / "settings.json")
    trade_repo = TradeRepository(settings.storage_path / "trades.json")
    market_data = MarketDataRepository(
        polygon_api_key=settings.polygon_api_key,
        finnhub_api_key=settings.finnhub_api_key,
    )

    ibkr = IBKRClient(
        settings.ibkr_host,
        settings.ibkr_port,
        settings.ibkr_client_id,
        settings.ibkr_account_id,
    )

    tradovate = TradovateClient(
        settings.tradovate_base_url,
        settings.tradovate_ws_url,
        settings.tradovate_username,
        settings.tradovate_password,
        settings.tradovate_cid,
        settings.tradovate_secret,
        settings.tradovate_app_id,
        settings.tradovate_app_version,
        settings.tradovate_device_id,
        settings.tradovate_account_id,
    )

    if settings.broker_enabled and settings.enable_ibkr:
        await ibkr.connect()

    if settings.broker_enabled and settings.enable_tradovate:
        await tradovate.connect()

    execution_router = ExecutionRouter(
        ibkr_client=ibkr,
        tradovate_client=tradovate,
    )

    scanner = ScannerService(
        market_data=market_data,
        settings_repo=settings_repo,
    )

    premarket_service = PremarketService(
        scanner=scanner,
        execution_router=execution_router,
        settings_repo=settings_repo,
        trade_repo=trade_repo,
    )

    midday_service = MiddayService(
        market_data=market_data,
        execution_router=execution_router,
        settings_repo=settings_repo,
        trade_repo=trade_repo,
    )

    postmarket_service = PostmarketService(
        trade_repo=trade_repo,
        settings_repo=settings_repo,
    )

    app_services = {
        "settings_repo": settings_repo,
        "trade_repo": trade_repo,
        "market_data": market_data,
        "ibkr": ibkr,
        "tradovate": tradovate,
        "execution_router": execution_router,
        "scanner": scanner,
        "premarket_service": premarket_service,
        "midday_service": midday_service,
        "postmarket_service": postmarket_service,
    }

    telegram_app = build_telegram_app(
        bot_token=settings.telegram_bot_token,
        admin_chat_id=settings.telegram_admin_chat_id,
        app_services=app_services,
        settings_repo=settings_repo,
    )

    scheduler = AsyncIOScheduler(timezone=settings.app_timezone)
    scheduler.add_job(premarket_service.run, trigger="cron", day_of_week="mon-fri", hour=6, minute=30)
    scheduler.add_job(midday_service.run, trigger="cron", day_of_week="mon-fri", hour=10, minute=0)
    scheduler.add_job(postmarket_service.run, trigger="cron", day_of_week="mon-fri", hour=13, minute=10)
    scheduler.add_job(postmarket_service.run_weekly_wrapup, trigger="cron", day_of_week="fri", hour=13, minute=30)
    scheduler.start()

    await telegram_app.initialize()
    await telegram_app.start()
    await telegram_app.updater.start_polling()

    try:
        await asyncio.Event().wait()
    finally:
        await telegram_app.updater.stop()
        await telegram_app.stop()
        await telegram_app.shutdown()
        scheduler.shutdown()
        await ibkr.close()
        await tradovate.close()


if __name__ == "__main__":
    asyncio.run(main())
