from __future__ import annotations

from data.sentiment import analyze_sentiment
from telegram_bot.formatters import format_daily_report, format_tomorrow_plan


class PostmarketService:
    def __init__(self, telegram_app, chat_id, news_client, trade_repo):
        self.telegram_app = telegram_app
        self.chat_id = chat_id
        self.news_client = news_client
        self.trade_repo = trade_repo

    def _tomorrow_plan(self, sentiment: dict, open_trades: list, closed_today: list) -> list[str]:
        plan = []

        if sentiment.get("sentiment") == "bearish":
            plan.append("Tomorrow bias: defensive. Respect weak breadth and avoid forcing breakouts.")
        elif sentiment.get("sentiment") == "bullish":
            plan.append("Tomorrow bias: constructive. Favor clean continuation names with real liquidity.")
        else:
            plan.append("Tomorrow bias: neutral. Let market breadth and the open determine aggression.")

        if open_trades:
            plan.append(f"Manage {len(open_trades)} open trade(s) before adding fresh exposure.")
        else:
            plan.append("No open bot-managed trades are carrying into tomorrow.")

        if closed_today:
            plan.append(f"{len(closed_today)} trade(s) closed today. Review which setups actually paid.")
        else:
            plan.append("No bot trades closed today. Check whether market quality or filters were the issue.")

        plan.append("Build tomorrow's watchlist around liquid names with catalysts and clean structure.")
        return plan

    async def run(self):
        headlines = await self.news_client.fetch_market_news()
        sentiment = analyze_sentiment(headlines)
        open_trades = self.trade_repo.get_open_trades()
        closed_today = (
            self.trade_repo.get_closed_trades_today()
            if hasattr(self.trade_repo, "get_closed_trades_today")
            else []
        )

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

        await self.telegram_app.bot.send_message(
            chat_id=self.chat_id,
            text=format_daily_report("🌙 9:00 PM Post-Market Wrap-Up", sections),
            parse_mode="HTML",
        )
        await self.telegram_app.bot.send_message(
            chat_id=self.chat_id,
            text=format_tomorrow_plan(self._tomorrow_plan(sentiment, open_trades, closed_today)),
            parse_mode="HTML",
        )

    async def run_weekly_wrapup(self):
        await self.telegram_app.bot.send_message(
            chat_id=self.chat_id,
            text=format_daily_report(
                "📆 Weekly Wrap-Up",
                {"Summary": ["Weekly wrap-up complete. Build Monday watchlists from strength, liquidity, and catalysts."]},
            ),
            parse_mode="HTML",
        )
