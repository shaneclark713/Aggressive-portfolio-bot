import pandas as pd

def normalize_backtest_feed(df: pd.DataFrame) -> pd.DataFrame:
    return df[['open','high','low','close','volume']].dropna().copy().sort_index()
