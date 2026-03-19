from __future__ import annotations

from typing import Any, Dict

import pandas as pd

from .base import BaseStrategy
from .indicators import adx, ema, sma
from .setup_models import SetupResult


class TrendFollowingStrategy(BaseStrategy):
    name = "Trend Following"

    def __init__(self, adx_threshold: int = 25):
        self.adx_threshold = adx_threshold

    def analyze(self, df: pd.DataFrame, symbol: str) -> Dict[str, Any]:
        required = {"high", "low", "close", "volume"}
        if df.empty or not required.issubset(df.columns):
            return SetupResult(symbol, "INVALID_DATA", self.name).as_dict()

        clean = df[list(required)].dropna().copy()
        if len(clean) < 50:
            return SetupResult(symbol, "INSUFFICIENT_DATA", self.name).as_dict()

        ema9 = ema(clean["close"], 9)
        sma21 = sma(clean["close"], 21)
        adx14 = adx(clean[["high", "low", "close"]], 14)
        vol_ratio = clean["volume"].iloc[-1] / clean["volume"].tail(20).mean()

        latest_close = float(clean["close"].iloc[-1])
        latest_ema9 = float(ema9.iloc[-1])
        latest_sma21 = float(sma21.iloc[-1])
        latest_adx = float(adx14.dropna().iloc[-1]) if not adx14.dropna().empty else 0.0

        signal = "WAIT"
        reasons = []
        confidence = 0

        if latest_adx >= self.adx_threshold:
            reasons.append("adx confirms trend strength")
            confidence += 25

        if latest_ema9 > latest_sma21 and latest_close > latest_ema9:
            signal = "LONG_TREND"
            reasons.extend(["ema9 above sma21", "price above ema9"])
            confidence += 35
        elif latest_ema9 < latest_sma21 and latest_close < latest_ema9:
            signal = "SHORT_TREND"
            reasons.extend(["ema9 below sma21", "price below ema9"])
            confidence += 35

        if vol_ratio >= 1.2:
            reasons.append("volume is above 20-bar average")
            confidence += 10

        return SetupResult(
            symbol=symbol,
            signal=signal,
            strategy=self.name,
            confidence=min(confidence, 95),
            trigger_reasons=reasons,
            metrics={
                "close_price": round(latest_close, 2),
                "ema_9": round(latest_ema9, 2),
                "sma_21": round(latest_sma21, 2),
                "adx_14": round(latest_adx, 2),
                "volume_ratio": round(float(vol_ratio), 2),
            },
        ).as_dict()
