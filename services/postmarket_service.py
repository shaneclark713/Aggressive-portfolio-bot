from data.sentiment import analyze_sentiment
from telegram_bot.formatters import format_daily_report

class PostmarketService:
    def __init__(self, telegram_app, chat_id, news_client, trade_repo): self.telegram_app=telegram_app; self.chat_id=chat_id; self.news_client=news_client; self.trade_repo=trade_repo
    async def run(self):
        headlines=await self.news_client.fetch_market_news(); sentiment=analyze_sentiment(headlines); open_trades=self.trade_repo.get_open_trades(); bullets=[f'After-hours sentiment: {sentiment["sentiment"]}', f'Open bot-managed trades: {len(open_trades)}']
        await self.telegram_app.bot.send_message(chat_id=self.chat_id, text=format_daily_report('🌙 9:00 PM End of Day Wrap-Up', bullets), parse_mode='HTML')
    async def run_weekly_wrapup(self):
        bullets=['Weekly summary complete.','Monday watchlist prep initiated.']
        await self.telegram_app.bot.send_message(chat_id=self.chat_id, text=format_daily_report('🗓️ Sunday 9:00 PM Weekly Wrap + Monday Prep', bullets), parse_mode='HTML')
