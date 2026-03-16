import pandas as pd
import pandas_ta as ta


class DivergenceStrategy:
    def __init__(self, lookback_period: int = 20): self.lookback=lookback_period
    def analyze(self, df: pd.DataFrame, symbol: str) -> dict:
        req=['high','low','close']
        if any(c not in df.columns for c in req): return {'symbol':symbol,'signal':'INVALID_DATA'}
        work=df[req].dropna().copy()
        if len(work) < self.lookback + 14: return {'symbol':symbol,'signal':'INSUFFICIENT_DATA'}
        work.ta.rsi(length=14, append=True)
        recent=work.iloc[-self.lookback:-1]; current=work.iloc[-1]; current_high=float(current['high']); current_low=float(current['low']); current_rsi=current.get('RSI_14')
        if pd.isna(current_rsi): return {'symbol':symbol,'signal':'INVALID_DATA'}
        prior_high_row=recent.loc[recent['high'].idxmax()]; prior_low_row=recent.loc[recent['low'].idxmin()]
        rsi_at_high=prior_high_row.get('RSI_14'); rsi_at_low=prior_low_row.get('RSI_14')
        signal='WAIT'
        if current_high > float(recent['high'].max()) and current_rsi < rsi_at_high and (current_rsi > 70 or rsi_at_high > 70): signal='SHORT_DIVERGENCE'
        elif current_low < float(recent['low'].min()) and current_rsi > rsi_at_low and (current_rsi < 30 or rsi_at_low < 30): signal='LONG_DIVERGENCE'
        return {'symbol':symbol,'signal':signal,'current_rsi':round(float(current_rsi),2)}
