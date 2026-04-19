from __future__ import annotations

from data.sentiment import analyze_sentiment
from telegram_bot.formatters import format_daily_report


class MiddayService:
    def __init__(
        self,
        telegram_app,
        chat_id,
        news_client,
        ibkr_client,
        tradovate_client,
        trade_repo,
        trade_review_service,
        discovery_service=None,
        config_service=None,
    ):
        self.telegram_app = telegram_app
        self.chat_id = chat_id
        self.news_client = news_client
        self.ibkr_client = ibkr_client
        self.tradovate_client = tradovate_client
        self.trade_repo = trade_repo
        self.trade_review_service = trade_review_service
        self.discovery_service = discovery_service
        self.config_service = config_service

    async def _market_snapshot_line_items(self) -> list[str]:
        if self.discovery_service is None:
            return ["Discovery snapshot: unavailable"]

        try:
            status = await self.discovery_service.snapshot_status("midday")
            return [
                f"Snapshot profile: {status.get('profile', 'midday')}",
                f"Snapshot rows: {status.get('row_count', 0)}",
                f"Snapshot source: {status.get('source', 'unknown')}",
            ]
        except Exception as exc:
            return [f"Discovery snapshot unavailable: {exc}"]

    async def run(self):
        headlines = await self.news_client.fetch_market_news()
        sentiment = analyze_sentiment(headlines)
        due = self.trade_review_service.due_for_daytrade_autoclose()
        open_trades = self.trade_repo.get_open_trades()
        execution_mode = self.config_service.get_execution_mode() if self.config_service else "unknown"
        preset = self.config_service.get_profile_preset("midday") if self.config_service else "unknown"

        sections = {
            "Market Overview": [
                f"Intra-day market sentiment: {sentiment['sentiment']} ({sentiment['score']})",
                f"Headlines loaded: {len(headlines)}",
                f"Execution mode: {execution_mode}",
                f"Midday preset: {preset}",
            ],
            "Bot State": [
                f"Open bot trades: {len(open_trades)}",
                f"Day trades due for closeout: {len(due)}",
            ],
            "Discovery State": await self._market_snapshot_line_items(),
            "Midday Read": [
                "Press winners only if they still respect structure.",
                "Cut weak names faster in chop conditions.",
                "Avoid opening fresh size right before scheduled economic releases.",
            ],
        }

        await self.telegram_app.bot.send_message(
            chat_id=self.chat_id,
            text=format_daily_report("☀️ 10:00 AM Mid-Day Review", sections),
            parse_mode="HTML",
        )
