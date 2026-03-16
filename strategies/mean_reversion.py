import pandas as pd
import pandas_ta as ta


class MeanReversionStrategy:
    def __init__(self, rsi_oversold: int = 30, rsi_overbought: int = 70): self.rsi_oversold=rsi_oversold; self.rsi_overbought=rsi_overbought
    def analyze(self, df: pd.DataFrame, symbol: str) -> dict:
        req=['open','high','low','close']
        if any(c not in df.columns for c in req): return {'symbol':symbol,'signal':'INVALID_DATA'}
        work=df[req].dropna().copy()
        if len(work) < 21: return {'symbol':symbol,'signal':'INSUFFICIENT_DATA'}
        work.ta.bbands(length=20, std=2, append=True); work.ta.rsi(length=14, append=True)
        prev=work.iloc[-2]; cur=work.iloc[-1]; current_close=float(cur['close']); current_open=float(cur['open']); current_rsi=cur.get('RSI_14'); prev_lower=prev.get('BBL_20_2.0'); prev_upper=prev.get('BBU_20_2.0'); mid=cur.get('BBM_20_2.0')
        if pd.isna(current_rsi) or pd.isna(prev_lower) or pd.isna(prev_upper) or pd.isna(mid): return {'symbol':symbol,'signal':'INVALID_DATA'}
        signal='WAIT'
        if float(prev['low']) < float(prev_lower) and current_rsi < self.rsi_oversold and current_close > current_open and current_close > float(prev['close']): signal='LONG_REVERSION'
        elif float(prev['high']) > float(prev_upper) and current_rsi > self.rsi_overbought and current_close < current_open and current_close < float(prev['close']): signal='SHORT_REVERSION'
        return {'symbol':symbol,'signal':signal,'mean_target':round(float(mid),2),'current_rsi':round(float(current_rsi),2)}
