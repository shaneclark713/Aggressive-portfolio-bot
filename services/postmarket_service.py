from __future__ import annotations

from data.sentiment import analyze_sentiment
from telegram_bot.formatters import format_daily_report


class PostmarketService:
    def __init__(self, telegram_app, chat_id, news_client, trade_repo):
        self.telegram_app = telegram_app
        self.chat_id = chat_id
        self.news_client = news_client
        self.trade_repo = trade_repo

    async def run(self):
        headlines = await self.news_client.fetch_market_news()
        sentiment = analyze_sentiment(headlines)
        open_trades = self.trade_repo.get_open_trades()
        closed_today = self.trade_repo.get_closed_trades_today() if hasattr(self.trade_repo, 'get_closed_trades_today') else []

        sections = {
            "After-Hours Overview": [
                f"After-hours sentiment: {sentiment['sentiment']} ({sentiment['score']})",
                f"Headlines loaded: {len(headlines)}",
            ],
            "Positions": [
                f"Open bot-managed trades: {len(open_trades)}",
                f"Closed trades today: {len(closed_today)}",
            ],
        }

        await self.telegram_app.bot.send_message(chat_id=self.chat_id, text=format_daily_report("🌙 9:00 PM Post-Market Wrap-Up", sections), parse_mode="HTML")

    async def run_weekly_wrapup(self):
        await self.telegram_app.bot.send_message(chat_id=self.chat_id, text=format_daily_report("📆 Weekly Wrap-Up", {"Summary": ["Weekly wrap-up placeholder ready for expansion."]}), parse_mode="HTML")
