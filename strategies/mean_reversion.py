from __future__ import annotations

from typing import Any, Dict

import pandas as pd

from .base import BaseStrategy
from .indicators import bollinger_bands, rsi
from .setup_models import SetupResult


class MeanReversionStrategy(BaseStrategy):
    name = "Mean Reversion"

    def __init__(self, rsi_oversold: int = 30, rsi_overbought: int = 70):
        self.rsi_oversold = rsi_oversold
        self.rsi_overbought = rsi_overbought

    def analyze(self, df: pd.DataFrame, symbol: str) -> Dict[str, Any]:
        required = {"open", "high", "low", "close"}
        if df.empty or not required.issubset(df.columns):
            return SetupResult(symbol, "INVALID_DATA", self.name).as_dict()

        work = df[list(required)].dropna().copy()
        if len(work) < 21:
            return SetupResult(symbol, "INSUFFICIENT_DATA", self.name).as_dict()

        bb = bollinger_bands(work["close"], 20, 2.0)
        work = pd.concat([work, bb], axis=1)
        work["rsi_14"] = rsi(work["close"], 14)

        prev_candle = work.iloc[-2]
        current_candle = work.iloc[-1]

        current_close = float(current_candle["close"])
        current_open = float(current_candle["open"])
        current_rsi = float(current_candle["rsi_14"])
        prev_close = float(prev_candle["close"])

        signal = "WAIT"
        reasons = []
        confidence = 0

        if float(prev_candle["low"]) < float(prev_candle["lower"]) and current_rsi < self.rsi_oversold:
            if current_close > current_open and current_close > prev_close:
                signal = "LONG_REVERSION"
                reasons.extend(["previous candle pierced lower band", "rsi is oversold", "current candle curled higher"])
                confidence = 70

        if float(prev_candle["high"]) > float(prev_candle["upper"]) and current_rsi > self.rsi_overbought:
            if current_close < current_open and current_close < prev_close:
                signal = "SHORT_REVERSION"
                reasons = ["previous candle pierced upper band", "rsi is overbought", "current candle rejected lower"]
                confidence = 70

        return SetupResult(
            symbol=symbol,
            signal=signal,
            strategy=self.name,
            confidence=confidence,
            trigger_reasons=reasons,
            metrics={
                "mean_target": round(float(current_candle["mid"]), 2),
                "current_rsi": round(current_rsi, 2),
                "current_close": round(current_close, 2),
            },
        ).as_dict()
