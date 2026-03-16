import pandas as pd

def add_atr(df: pd.DataFrame, length:int=14) -> pd.DataFrame:
    work=df.copy(); work.ta.atr(length=length, append=True); return work

def add_rsi_bbands(df: pd.DataFrame) -> pd.DataFrame:
    work=df.copy(); work.ta.rsi(length=14, append=True); work.ta.bbands(length=20, std=2, append=True); return work
