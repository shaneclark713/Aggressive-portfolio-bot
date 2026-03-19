from __future__ import annotations

from typing import Any, Dict

import pandas as pd

from .base import BaseStrategy
from .setup_models import SetupResult


class BreakoutBoxStrategy(BaseStrategy):
    name = "Breakout Box"

    def __init__(
        self,
        lookback_candles: int = 20,
        max_box_width_pct: float = 0.025,
        breakout_buffer_pct: float = 0.001,
        volume_surge_multiple: float = 1.5,
    ):
        self.lookback = lookback_candles
        self.max_box_width_pct = max_box_width_pct
        self.breakout_buffer_pct = breakout_buffer_pct
        self.volume_surge_multiple = volume_surge_multiple

    def analyze(self, df: pd.DataFrame, symbol: str) -> Dict[str, Any]:
        required = ["high", "low", "close", "volume"]
        if any(col not in df.columns for col in required):
            return SetupResult(symbol, "INVALID_DATA", self.name).as_dict()

        clean = df[required].dropna().copy()
        if len(clean) < self.lookback + 1:
            return SetupResult(symbol, "INSUFFICIENT_DATA", self.name).as_dict()

        recent = clean.iloc[-self.lookback - 1 : -1]
        current = clean.iloc[-1]

        box_high = float(recent["high"].max())
        box_low = float(recent["low"].min())
        if box_low <= 0:
            return SetupResult(symbol, "INVALID_DATA", self.name).as_dict()

        box_width_pct = (box_high - box_low) / box_low
        upper_trigger = box_high * (1 + self.breakout_buffer_pct)
        lower_trigger = box_low * (1 - self.breakout_buffer_pct)

        half = max(1, self.lookback // 2)
        vol_first = float(recent["volume"].iloc[:half].mean())
        vol_second = float(recent["volume"].iloc[half:].mean())
        current_volume = float(current["volume"])
        current_close = float(current["close"])

        contraction = vol_second < vol_first if vol_first > 0 else False
        volume_ratio_now = current_volume / vol_second if vol_second > 0 else 0.0
        volume_surge = vol_second > 0 and volume_ratio_now >= self.volume_surge_multiple

        signal = "WAIT"
        reasons = []
        confidence = 0

        if box_width_pct <= self.max_box_width_pct:
            reasons.append("box width is tight")
            confidence += 20

        if contraction:
            reasons.append("volume contracted inside box")
            confidence += 20

        if volume_surge:
            reasons.append("breakout volume expanded")
            confidence += 20

        if current_close > upper_trigger and volume_surge and box_width_pct <= self.max_box_width_pct:
            signal = "LONG_BREAKOUT"
            reasons.append("close broke above box high")
            confidence += 25
        elif current_close < lower_trigger and volume_surge and box_width_pct <= self.max_box_width_pct:
            signal = "SHORT_BREAKOUT"
            reasons.append("close broke below box low")
            confidence += 25

        return SetupResult(
            symbol=symbol,
            signal=signal,
            strategy=self.name,
            confidence=min(confidence, 95),
            trigger_reasons=reasons,
            metrics={
                "box_high": round(box_high, 4),
                "box_low": round(box_low, 4),
                "box_width_pct": round(box_width_pct * 100, 2),
                "volume_ratio": round(volume_ratio_now, 2),
            },
            metadata={"upper_trigger": round(upper_trigger, 4), "lower_trigger": round(lower_trigger, 4)},
        ).as_dict()
