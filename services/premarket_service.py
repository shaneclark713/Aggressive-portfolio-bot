from datetime import datetime
from zoneinfo import ZoneInfo
from data.sentiment import analyze_sentiment
from telegram_bot.formatters import format_daily_report, format_trade_alert
from telegram_bot.keyboards import build_trade_keyboard

class PremarketService:
    def __init__(self, telegram_app, chat_id, news_client, econ_client, watchlist_service, scanner_service, alert_service, config_service, alert_repo):
        self.telegram_app=telegram_app; self.chat_id=chat_id; self.news_client=news_client; self.econ_client=econ_client; self.watchlist_service=watchlist_service; self.scanner_service=scanner_service; self.alert_service=alert_service; self.config_service=config_service; self.alert_repo=alert_repo
    async def run(self):
        today_ny=datetime.now(ZoneInfo('America/New_York')).date(); econ_events=await self.econ_client.fetch_events(today_ny); headlines=await self.news_client.fetch_market_news(); sentiment=analyze_sentiment(headlines); watchlists=await self.watchlist_service.build_watchlists(); day_candidates=await self.scanner_service.scan_day_trade_candidates()
        bullets=[f'Active preset: {self.config_service.get_active_preset()}', f'Market sentiment: {sentiment["sentiment"]} ({sentiment["score"]})', f'Economic events today: {len(econ_events)}', f'Day trade universe: {", ".join(watchlists["day_trade_equities"])}', f'Swing trade universe: {", ".join(watchlists["swing_trade_equities"])}', f'Futures universe: {", ".join(watchlists["futures"])}']
        await self.telegram_app.bot.send_message(chat_id=self.chat_id, text=format_daily_report('🌅 5:30 AM Pre-Market Report', bullets), parse_mode='HTML')
        for payload in day_candidates:
            trade_id=self.alert_service.create_trade_candidate(payload, broker='IBKR', instrument_type='stock')
            text=format_trade_alert({**payload, 'trade_id':trade_id}); msg=await self.telegram_app.bot.send_message(chat_id=self.chat_id, text=text, reply_markup=build_trade_keyboard(trade_id), parse_mode='HTML'); self.alert_repo.set_message_id(trade_id, msg.message_id)
