import pandas as pd
import pandas_ta as ta


class TrendFollowingStrategy:
    def __init__(self, adx_threshold: int = 25): self.adx_threshold=adx_threshold
    def analyze(self, df: pd.DataFrame, symbol: str) -> dict:
        req=['high','low','close']
        if any(c not in df.columns for c in req): return {'symbol':symbol,'signal':'INVALID_DATA'}
        work=df[req].dropna().copy()
        if len(work) < 50: return {'symbol':symbol,'signal':'INSUFFICIENT_DATA'}
        work.ta.ema(length=9, append=True); work.ta.sma(length=21, append=True); work.ta.adx(length=14, append=True)
        latest=work.iloc[-1]; close=float(latest['close']); ema=latest.get('EMA_9'); sma=latest.get('SMA_21'); adx=latest.get('ADX_14')
        if pd.isna(ema) or pd.isna(sma) or pd.isna(adx): return {'symbol':symbol,'signal':'INVALID_DATA'}
        signal='WAIT'
        if adx > self.adx_threshold:
            if ema > sma and close > ema: signal='LONG_TREND'
            elif ema < sma and close < ema: signal='SHORT_TREND'
        return {'symbol':symbol,'signal':signal,'adx_strength':round(float(adx),2)}
