import logging
from typing import Dict, Any, List

import pandas as pd

logger = logging.getLogger("aggressive_portfolio_bot.strategies.breakout_box")


class BreakoutBoxStrategy:
    def __init__(
        self,
        lookback_candles: int = 20,
        max_box_width_pct: float = 0.025,
        breakout_buffer_pct: float = 0.001,
        volume_surge_multiple: float = 1.5,
    ):
        """
        Args:
            lookback_candles: Number of candles used to define the box.
            max_box_width_pct: Max allowed box width as decimal (0.025 = 2.5%).
            breakout_buffer_pct: Minimum close beyond box boundary to confirm breakout.
            volume_surge_multiple: Required multiple of recent avg volume for breakout confirmation.
        """
        self.lookback = lookback_candles
        self.max_box_width_pct = max_box_width_pct
        self.breakout_buffer_pct = breakout_buffer_pct
        self.volume_surge_multiple = volume_surge_multiple

    def analyze(self, df: pd.DataFrame, symbol: str) -> Dict[str, Any]:
        required_cols: List[str] = ["high", "low", "close", "volume"]
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            logger.warning("Missing required columns for %s: %s", symbol, missing_cols)
            return {
                "symbol": symbol,
                "signal": "INVALID_DATA",
                "reason": f"Missing columns: {missing_cols}",
            }

        clean_df = df[required_cols].dropna().copy()
        if len(clean_df) < self.lookback + 1:
            logger.warning("Insufficient data for %s to run Breakout Box.", symbol)
            return {
                "symbol": symbol,
                "signal": "INSUFFICIENT_DATA",
            }

        # Box = recent completed candles only (exclude current active candle)
        recent_data = clean_df.iloc[-self.lookback - 1:-1]
        current_candle = clean_df.iloc[-1]

        box_high = float(recent_data["high"].max())
        box_low = float(recent_data["low"].min())

        if box_low <= 0:
            logger.warning("Invalid box_low for %s: %s", symbol, box_low)
            return {
                "symbol": symbol,
                "signal": "INVALID_DATA",
                "reason": "box_low <= 0",
            }

        box_width = (box_high - box_low) / box_low
        is_tight_box = box_width <= self.max_box_width_pct

        half_lookback = max(1, self.lookback // 2)
        vol_first_half = float(recent_data["volume"].iloc[:half_lookback].mean())
        vol_second_half = float(recent_data["volume"].iloc[half_lookback:].mean())

        volume_dropping = vol_second_half < vol_first_half if vol_first_half > 0 else False

        current_close = float(current_candle["close"])
        current_volume = float(current_candle["volume"])

        upper_breakout_level = box_high * (1 + self.breakout_buffer_pct)
        lower_breakout_level = box_low * (1 - self.breakout_buffer_pct)

        volume_surge = (
            vol_second_half > 0 and current_volume >= vol_second_half * self.volume_surge_multiple
        )

        signal = "WAIT"

        if is_tight_box and volume_dropping:
            if current_close > upper_breakout_level and volume_surge:
                signal = "LONG_BREAKOUT"
            elif current_close < lower_breakout_level and volume_surge:
                signal = "SHORT_BREAKOUT"
            else:
                signal = "CONSOLIDATING"

        return {
            "symbol": symbol,
            "signal": signal,
            "box_high": round(box_high, 4),
            "box_low": round(box_low, 4),
            "box_width_pct": round(box_width * 100, 2),
            "volume_dropping": volume_dropping,
            "vol_first_half": round(vol_first_half, 2),
            "vol_second_half": round(vol_second_half, 2),
            "volume_surge": volume_surge,
            "current_close": round(current_close, 4),
            "current_volume": round(current_volume, 2),
            "upper_breakout_level": round(upper_breakout_level, 4),
            "lower_breakout_level": round(lower_breakout_level, 4),
        }
