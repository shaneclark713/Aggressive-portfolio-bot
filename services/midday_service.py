from data.sentiment import analyze_sentiment
from telegram_bot.formatters import format_daily_report

class MiddayService:
    def __init__(self, telegram_app, chat_id, news_client, ibkr_client, tradovate_client, trade_repo, trade_review_service):
        self.telegram_app=telegram_app; self.chat_id=chat_id; self.news_client=news_client; self.ibkr_client=ibkr_client; self.tradovate_client=tradovate_client; self.trade_repo=trade_repo; self.trade_review_service=trade_review_service
    async def run(self):
        headlines=await self.news_client.fetch_market_news(); sentiment=analyze_sentiment(headlines); ib_positions=await self.ibkr_client.get_positions() if self.ibkr_client.is_connected() else []; td_orders=await self.tradovate_client.get_open_orders() if self.tradovate_client.token else []
        bullets=[f'Intra-day market sentiment: {sentiment["sentiment"]}', f'IBKR positions tracked: {len(ib_positions)}', f'Tradovate open orders: {len(td_orders)}', f'Open bot trades: {len(self.trade_repo.get_open_trades())}']
        due=self.trade_review_service.due_for_daytrade_autoclose()
        if due: bullets.append(f'Day trades due for 3:45 PM NY closeout: {len(due)}')
        await self.telegram_app.bot.send_message(chat_id=self.chat_id, text=format_daily_report('☀️ 10:00 AM Mid-Day Review', bullets), parse_mode='HTML')
