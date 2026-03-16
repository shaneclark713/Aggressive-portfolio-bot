from __future__ import annotations
from datetime import datetime, timedelta, timezone
import pandas_ta as ta
from config.universe import CORE_EQUITIES, CORE_FUTURES, DAY_TRADE_SETTINGS, SWING_TRADE_SETTINGS, EXCLUDED_TICKERS

class UniverseFilter:
    def __init__(self, market_client): self.market_client=market_client
    async def build_daily_watchlist(self) -> dict:
        end=datetime.now(timezone.utc).date(); start=end-timedelta(days=90)
        day_list=[]; swing_list=[]
        for symbol in CORE_EQUITIES:
            if symbol in EXCLUDED_TICKERS: continue
            df=await self.market_client.get_historical_data(symbol=symbol, multiplier=1, timespan='day', start_date=start.isoformat(), end_date=end.isoformat())
            if df.empty or len(df)<20: continue
            metrics=self._compute_metrics(df)
            if self._passes(metrics, DAY_TRADE_SETTINGS): day_list.append(symbol)
            if self._passes(metrics, SWING_TRADE_SETTINGS): swing_list.append(symbol)
        return {'day_trade_equities':sorted(set(day_list)),'swing_trade_equities':sorted(set(swing_list)),'futures':CORE_FUTURES}
    def _compute_metrics(self, df):
        work=df[['open','high','low','close','volume']].dropna().copy().tail(30)
        work.ta.atr(length=14, append=True)
        latest=work.iloc[-1]; prev=work.iloc[-2]
        price=float(latest['close']); avg_volume=float(work['volume'].tail(20).mean())
        atr_pct=float(latest['ATR_14'])/price if price else 0.0
        gap_pct=abs(float(latest['open'])-float(prev['close']))/float(prev['close']) if float(prev['close']) else 0.0
        return {'current_price':price,'avg_daily_volume':avg_volume,'atr_pct':atr_pct,'gap_pct':gap_pct,'relative_volume':1.0}
    def _passes(self, metrics:dict, settings:dict) -> bool:
        return metrics['current_price']>=settings['min_price'] and metrics['avg_daily_volume']>=settings['min_avg_daily_volume'] and metrics['atr_pct']>=settings['min_atr_pct'] and metrics['gap_pct']<=settings['max_gap_pct'] and metrics['relative_volume']>=settings['min_relative_volume']
