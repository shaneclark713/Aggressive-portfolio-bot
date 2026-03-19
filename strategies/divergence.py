import logging
from typing import Dict, Any, List

import pandas as pd

logger = logging.getLogger("aggressive_portfolio_bot.strategies.divergence")


class DivergenceStrategy:
    def __init__(self, lookback_period: int = 20):
        self.lookback = lookback_period

    def _rsi(self, close: pd.Series, length: int = 14) -> pd.Series:
        delta = close.diff()

        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)

        avg_gain = gain.rolling(window=length, min_periods=length).mean()
        avg_loss = loss.rolling(window=length, min_periods=length).mean()

        rs = avg_gain / avg_loss.replace(0, pd.NA)
        rsi = 100 - (100 / (1 + rs))

        # Handle edge cases cleanly
        rsi = rsi.fillna(50)
        rsi = rsi.clip(lower=0, upper=100)
        return rsi

    def analyze(self, df: pd.DataFrame, symbol: str) -> Dict[str, Any]:
        required_cols: List[str] = ["high", "low", "close"]
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            return {
                "symbol": symbol,
                "signal": "INVALID_DATA",
                "reason": f"Missing columns: {missing_cols}",
            }

        work_df = df[required_cols].dropna().copy()
        if len(work_df) < self.lookback + 14:
            return {"symbol": symbol, "signal": "INSUFFICIENT_DATA"}

        work_df["RSI_14"] = self._rsi(work_df["close"], length=14)

        recent_window = work_df.iloc[-self.lookback:-1]
        current_candle = work_df.iloc[-1]

        current_high = float(current_candle["high"])
        current_low = float(current_candle["low"])
        current_close = float(current_candle["close"])
        current_rsi = current_candle.get("RSI_14")

        if pd.isna(current_rsi):
            return {
                "symbol": symbol,
                "signal": "INVALID_DATA",
                "reason": "Current RSI unavailable",
            }

        highest_price_recent = float(recent_window["high"].max())
        lowest_price_recent = float(recent_window["low"].min())

        prior_high_row = recent_window.loc[recent_window["high"].idxmax()]
        prior_low_row = recent_window.loc[recent_window["low"].idxmin()]

        rsi_at_high = prior_high_row.get("RSI_14")
        rsi_at_low = prior_low_row.get("RSI_14")

        if pd.isna(rsi_at_high) or pd.isna(rsi_at_low):
            return {
                "symbol": symbol,
                "signal": "INVALID_DATA",
                "reason": "Historical RSI unavailable",
            }

        signal = "WAIT"

        # Bearish divergence: higher high in price, lower high in RSI
        if current_high > highest_price_recent and current_rsi < rsi_at_high:
            if current_rsi > 70 or rsi_at_high > 70:
                signal = "SHORT_DIVERGENCE"

        # Bullish divergence: lower low in price, higher low in RSI
        elif current_low < lowest_price_recent and current_rsi > rsi_at_low:
            if current_rsi < 30 or rsi_at_low < 30:
                signal = "LONG_DIVERGENCE"

        return {
            "symbol": symbol,
            "signal": signal,
            "current_close": round(current_close, 2),
            "current_rsi": round(float(current_rsi), 2),
            "prior_high_rsi": round(float(rsi_at_high), 2),
            "prior_low_rsi": round(float(rsi_at_low), 2),
            "divergence_confirmed": signal != "WAIT",
        }
