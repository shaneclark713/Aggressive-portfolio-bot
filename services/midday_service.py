from __future__ import annotations

from data.sentiment import analyze_sentiment
from telegram_bot.formatters import format_daily_report


class MiddayService:
    def __init__(self, telegram_app, chat_id, news_client, stock_client, options_client, trade_repo, trade_review_service):
        self.telegram_app = telegram_app
        self.chat_id = chat_id
        self.news_client = news_client
        # Backward-compatible constructor slots. Current active stack is Alpaca + Tradier;
        # older app wiring may still pass these as None.
        self.stock_client = stock_client
        self.options_client = options_client
        self.trade_repo = trade_repo
        self.trade_review_service = trade_review_service

    async def _safe_positions(self, client) -> list:
        if client is None or not hasattr(client, "get_positions"):
            return []
        try:
            positions = await client.get_positions()
            return positions if isinstance(positions, list) else []
        except Exception:
            return []

    async def run(self):
        headlines = await self.news_client.fetch_market_news()
        sentiment = analyze_sentiment(headlines)
        stock_positions = await self._safe_positions(self.stock_client)
        option_positions = await self._safe_positions(self.options_client)
        due = self.trade_review_service.due_for_daytrade_autoclose()
        open_trades = self.trade_repo.get_open_trades()

        sections = {
            "Market Overview": [
                f"Intra-day market sentiment: {sentiment['sentiment']} ({sentiment['score']})",
                f"Headlines loaded: {len(headlines)}",
            ],
            "Broker State": [
                "Stock broker: Alpaca",
                "Options broker: Tradier",
                f"Synced stock positions: {len(stock_positions)}",
                f"Synced option positions: {len(option_positions)}",
            ],
            "Bot State": [
                f"Open bot trades: {len(open_trades)}",
                f"Day trades due for 3:45 PM NY closeout: {len(due)}",
            ],
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
