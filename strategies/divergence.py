from __future__ import annotations

from typing import Any, Dict

import pandas as pd

from .base import BaseStrategy
from .indicators import rsi
from .setup_models import SetupResult


class DivergenceStrategy(BaseStrategy):
    name = "Divergence"

    def __init__(self, lookback_period: int = 20):
        self.lookback = lookback_period

    def analyze(self, df: pd.DataFrame, symbol: str) -> Dict[str, Any]:
        required = {"high", "low", "close"}
        if df.empty or not required.issubset(df.columns):
            return SetupResult(symbol, "INVALID_DATA", self.name).as_dict()

        work = df[list(required)].dropna().copy()
        if len(work) < self.lookback + 14:
            return SetupResult(symbol, "INSUFFICIENT_DATA", self.name).as_dict()

        work["rsi_14"] = rsi(work["close"], 14)
        recent = work.iloc[-self.lookback:-1]
        current = work.iloc[-1]

        current_high = float(current["high"])
        current_low = float(current["low"])
        current_close = float(current["close"])
        current_rsi = float(current["rsi_14"])

        highest = float(recent["high"].max())
        lowest = float(recent["low"].min())
        rsi_at_high = float(recent.loc[recent["high"].idxmax(), "rsi_14"])
        rsi_at_low = float(recent.loc[recent["low"].idxmin(), "rsi_14"])

        signal = "WAIT"
        reasons = []
        confidence = 0

        if current_high > highest and current_rsi < rsi_at_high and (current_rsi > 70 or rsi_at_high > 70):
            signal = "SHORT_DIVERGENCE"
            reasons.extend(["price made higher high", "rsi made lower high", "overbought divergence confirmed"])
            confidence = 78
        elif current_low < lowest and current_rsi > rsi_at_low and (current_rsi < 30 or rsi_at_low < 30):
            signal = "LONG_DIVERGENCE"
            reasons.extend(["price made lower low", "rsi made higher low", "oversold divergence confirmed"])
            confidence = 78

        return SetupResult(
            symbol=symbol,
            signal=signal,
            strategy=self.name,
            confidence=confidence,
            trigger_reasons=reasons,
            metrics={
                "current_close": round(current_close, 2),
                "current_rsi": round(current_rsi, 2),
                "prior_high_rsi": round(rsi_at_high, 2),
                "prior_low_rsi": round(rsi_at_low, 2),
            },
        ).as_dict()
