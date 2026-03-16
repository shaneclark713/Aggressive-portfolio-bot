from datetime import datetime
from zoneinfo import ZoneInfo


class TradeReviewService:
    def __init__(self, trade_repo, settings):
        self.trade_repo = trade_repo
        self.settings = settings

    def due_for_daytrade_autoclose(self):
        now = datetime.now(ZoneInfo('America/New_York')).strftime('%H:%M')
        if now < self.settings.bot_day_trade_auto_close_time_ny:
            return []
        return [t for t in self.trade_repo.get_open_trades() if t['horizon'] == 'DAY_TRADE']
