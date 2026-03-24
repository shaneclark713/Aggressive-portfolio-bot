from __future__ import annotations

import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from data.sentiment import analyze_sentiment
from telegram_bot.formatters import (
    format_daily_report,
    format_trade_alert,
    format_scan_status,
)
from telegram_bot.keyboards import build_trade_keyboard

logger = logging.getLogger("aggressive_portfolio_bot.services.premarket")


class PremarketService:
    def __init__(
        self,
        telegram_app,
        chat_id,
        news_client,
        econ_client,
        watchlist_service,
        scanner_service,
        alert_service,
        config_service,
        alert_repo,
    ):
        self.telegram_app = telegram_app
        self.chat_id = chat_id
        self.news_client = news_client
        self.econ_client = econ_client
        self.watchlist_service = watchlist_service
        self.scanner_service = scanner_service
        self.alert_service = alert_service
        self.config_service = config_service
        self.alert_repo = alert_repo

    async def run(self):
        today_ny = datetime.now(ZoneInfo("America/New_York")).date()

        try:
            econ_events = await self.econ_client.fetch_events(today_ny)
            econ_status = "loaded"
        except Exception as exc:
            econ_events = []
            econ_status = "unavailable"
            logger.warning("Premarket econ calendar unavailable: %s", exc)

        try:
            headlines = await self.news_client.fetch_market_news()
            news_status = "loaded"
        except Exception as exc:
            headlines = []
            news_status = "unavailable"
            logger.warning("Premarket news feed unavailable: %s", exc)

        sentiment = analyze_sentiment(headlines) if headlines else {
            "sentiment": "NEUTRAL",
            "score": 0,
        }

        try:
            watchlists = await self.watchlist_service.build_watchlists()
        except Exception as exc:
            logger.exception("Premarket watchlist build failed: %s", exc)
            await self.telegram_app.bot.send_message(
                chat_id=self.chat_id,
                text=(
                    "🌅 <b>5:30 AM Pre-Market Report</b>\n\n"
                    "<b>Status:</b> Watchlist build failed.\n"
                    f"<b>Error:</b> {exc}"
                ),
                parse_mode="HTML",
            )
            return

        try:
            day_candidates = await self.scanner_service.scan_day_trade_candidates()
        except Exception as exc:
            logger.exception("Premarket scan failed: %s", exc)
            day_candidates = []

        scan_stats = self.scanner_service.get_last_scan_stats()
        high_impact = [event for event in econ_events if event.get("impact_label") == "high"]

        sections = {
            "Configuration": [
                f"Active preset: {self.config_service.get_active_preset()}",
                f"Execution mode: {self.config_service.get_execution_mode()}",
            ],
            "Market Overview": [
                f"Market sentiment: {sentiment['sentiment']} ({sentiment['score']})",
                f"Economic events today: {len(econ_events)} ({econ_status})",
                f"High-impact events: {len(high_impact)}",
                f"Top headlines loaded: {len(headlines)} ({news_status})",
            ],
            "Universe": [
                f"Day trade universe: {len(watchlists.get('day_trade_equities', []))}",
                f"Swing trade universe: {len(watchlists.get('swing_trade_equities', []))}",
                f"Futures universe: {len(watchlists.get('futures', []))}",
            ],
            "Scan": [
                f"Universe loaded: {scan_stats.get('universe_loaded', 0)}",
                f"Passed universe filters: {scan_stats.get('passed_universe_filters', 0)}",
                f"Symbols evaluated: {scan_stats.get('evaluated', 0)}",
                f"Qualified setups: {scan_stats.get('qualified', 0)}",
                f"Rate limited: {scan_stats.get('rate_limited', 0)}",
                f"Errors: {scan_stats.get('errors', 0)}",
            ],
        }

        await self.telegram_app.bot.send_message(
            chat_id=self.chat_id,
            text=format_daily_report("🌅 5:30 AM Pre-Market Report", sections),
            parse_mode="HTML",
        )

        await self.telegram_app.bot.send_message(
            chat_id=self.chat_id,
            text=format_scan_status(scan_stats),
            parse_mode="HTML",
        )

        for payload in day_candidates:
            try:
                trade_id = await self.alert_service.create_trade_candidate(
                    payload,
                    broker="ALPACA",
                    instrument_type="stock",
                )

                text = format_trade_alert({**payload, "trade_id": trade_id})

                msg = await self.telegram_app.bot.send_message(
                    chat_id=self.chat_id,
                    text=text,
                    reply_markup=build_trade_keyboard(trade_id),
                    parse_mode="HTML",
                )

                if hasattr(self.alert_repo, "set_message_id"):
                    self.alert_repo.set_message_id(trade_id, msg.message_id)

            except Exception as exc:
                logger.exception(
                    "Failed to send/store premarket trade candidate for %s: %s",
                    payload.get("symbol", "UNKNOWN"),
                    exc,
                )
