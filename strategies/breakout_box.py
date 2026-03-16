import pandas as pd


class BreakoutBoxStrategy:
    def __init__(self, lookback_candles: int = 20, max_box_width_pct: float = 0.025, breakout_buffer_pct: float = 0.001, volume_surge_multiple: float = 1.5):
        self.lookback=lookback_candles; self.max_box_width_pct=max_box_width_pct; self.breakout_buffer_pct=breakout_buffer_pct; self.volume_surge_multiple=volume_surge_multiple
    def analyze(self, df: pd.DataFrame, symbol: str) -> dict:
        required=['high','low','close','volume']
        if any(c not in df.columns for c in required): return {'symbol':symbol,'signal':'INVALID_DATA'}
        clean=df[required].dropna().copy()
        if len(clean) < self.lookback + 1: return {'symbol':symbol,'signal':'INSUFFICIENT_DATA'}
        recent=clean.iloc[-self.lookback-1:-1]; current=clean.iloc[-1]
        box_high=float(recent['high'].max()); box_low=float(recent['low'].min())
        if box_low <= 0: return {'symbol':symbol,'signal':'INVALID_DATA'}
        box_width=(box_high-box_low)/box_low; half=max(1,self.lookback//2)
        vol_first=float(recent['volume'].iloc[:half].mean()); vol_second=float(recent['volume'].iloc[half:].mean())
        volume_dropping = vol_second < vol_first if vol_first > 0 else False
        upper=box_high*(1+self.breakout_buffer_pct); lower=box_low*(1-self.breakout_buffer_pct)
        close=float(current['close']); current_vol=float(current['volume']); volume_surge=vol_second > 0 and current_vol >= vol_second*self.volume_surge_multiple
        signal='WAIT'
        if box_width <= self.max_box_width_pct and volume_dropping:
            if close > upper and volume_surge: signal='LONG_BREAKOUT'
            elif close < lower and volume_surge: signal='SHORT_BREAKOUT'
            else: signal='CONSOLIDATING'
        return {'symbol':symbol,'signal':signal,'box_high':round(box_high,4),'box_low':round(box_low,4),'box_width_pct':round(box_width*100,2)}
