from __future__ import annotations

import pandas as pd

from .indicators import adx, ema, sma


class MarketRegimeClassifier:
    def classify(self, df: pd.DataFrame) -> str:
        required = {"high", "low", "close"}
        if df.empty or len(df) < 30 or not required.issubset(df.columns):
            return "UNKNOWN"

        work = df[["high", "low", "close"]].dropna().copy()
        if len(work) < 30:
            return "UNKNOWN"

        adx_value = adx(work, 14).dropna()
        if adx_value.empty:
            return "UNKNOWN"

        close = float(work["close"].iloc[-1])
        ema9 = float(ema(work["close"], 9).iloc[-1])
        sma21 = float(sma(work["close"], 21).iloc[-1])
        regime_adx = float(adx_value.iloc[-1])

        if regime_adx >= 25 and close > ema9 > sma21:
            return "TREND_UP"
        if regime_adx >= 25 and close < ema9 < sma21:
            return "TREND_DOWN"
        if regime_adx < 20:
            return "RANGE"
        return "TRANSITION"
