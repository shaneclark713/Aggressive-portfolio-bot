from __future__ import annotations

from datetime import datetime
from html import escape
from typing import Any
from zoneinfo import ZoneInfo


class Spy0DteService:
    """Analysis-only SPY/XSP market-structure report service."""

    def __init__(self, telegram_app, chat_id: int, market_client, news_client, econ_client, tradier_client=None):
        self.telegram_app = telegram_app
        self.chat_id = chat_id
        self.market_client = market_client
        self.news_client = news_client
        self.econ_client = econ_client
        self.tradier_client = tradier_client
        self.market_tz = ZoneInfo("America/New_York")

    async def analyze(self) -> dict[str, Any]:
        return {
            "timestamp": datetime.now(self.market_tz).isoformat(timespec="seconds"),
            "status": "service_connected",
            "message": "SPY/XSP analysis service is wired and ready for indicator expansion.",
        }

    def format_report(self, payload: dict[str, Any], title: str) -> str:
        return "\n".join([
            f"<b>{escape(title)}</b>",
            f"<i>{escape(str(payload.get('timestamp', '')))}</i>",
            "",
            "<b>STATUS</b>",
            f"• {escape(str(payload.get('message', 'SPY/XSP service connected.')))}",
        ])

    async def run_breakdown(self) -> dict[str, Any]:
        payload = await self.analyze()
        await self.telegram_app.bot.send_message(
            chat_id=self.chat_id,
            text=self.format_report(payload, "🧭 6:15 AM SPY/XSP 0DTE Direction Desk"),
            parse_mode="HTML",
        )
        return payload

    async def run_midday(self) -> dict[str, Any]:
        payload = await self.analyze()
        await self.telegram_app.bot.send_message(
            chat_id=self.chat_id,
            text=self.format_report(payload, "☀️ 10:00 AM ET SPY/XSP 0DTE Midday Desk"),
            parse_mode="HTML",
        )
        return payload
