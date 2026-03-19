import logging
from typing import Dict, Any, List

import pandas as pd

logger = logging.getLogger("aggressive_portfolio_bot.strategies.mean_reversion")


class MeanReversionStrategy:
    def __init__(self, rsi_oversold: int = 30, rsi_overbought: int = 70):
        self.rsi_oversold = rsi_oversold
        self.rsi_overbought = rsi_overbought

    def _rsi(self, close: pd.Series, length: int = 14) -> pd.Series:
        delta = close.diff()

        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)

        avg_gain = gain.rolling(window=length, min_periods=length).mean()
        avg_loss = loss.rolling(window=length, min_periods=length).mean()

        rs = avg_gain / avg_loss.replace(0, pd.NA)
        rsi = 100 - (100 / (1 + rs))
        rsi = rsi.fillna(50).clip(lower=0, upper=100)
        return rsi

    def _bollinger_bands(
        self, close: pd.Series, length: int = 20, std_mult: float = 2.0
    ) -> pd.DataFrame:
        mid = close.rolling(window=length, min_periods=length).mean()
        std = close.rolling(window=length, min_periods=length).std(ddof=0)

        lower = mid - (std * std_mult)
        upper = mid + (std * std_mult)

        return pd.DataFrame(
            {
                "BBL_20_2.0": lower,
                "BBM_20_2.0": mid,
                "BBU_20_2.0": upper,
            },
            index=close.index,
        )

    def analyze(self, df: pd.DataFrame, symbol: str) -> Dict[str, Any]:
        required_cols: List[str] = ["open", "high", "low", "close"]
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            logger.warning("Missing required columns for %s: %s", symbol, missing_cols)
            return {
                "symbol": symbol,
                "signal": "INVALID_DATA",
                "reason": f"Missing columns: {missing_cols}",
            }

        work_df = df[required_cols].dropna().copy()
        if len(work_df) < 21:
            return {
                "symbol": symbol,
                "signal": "INSUFFICIENT_DATA",
            }

        bb = self._bollinger_bands(work_df["close"], length=20, std_mult=2.0)
        work_df = pd.concat([work_df, bb], axis=1)
        work_df["RSI_14"] = self._rsi(work_df["close"], length=14)

        prev_candle = work_df.iloc[-2]
        current_candle = work_df.iloc[-1]

        current_close = float(current_candle["close"])
        current_open = float(current_candle["open"])
        current_rsi = current_candle.get("RSI_14")

        prev_close = float(prev_candle["close"])
        prev_low = float(prev_candle["low"])
        prev_high = float(prev_candle["high"])

        prev_lower_bb = prev_candle.get("BBL_20_2.0")
        prev_upper_bb = prev_candle.get("BBU_20_2.0")
        mid_bb = current_candle.get("BBM_20_2.0")

        if (
            pd.isna(current_rsi)
            or pd.isna(prev_lower_bb)
            or pd.isna(prev_upper_bb)
            or pd.isna(mid_bb)
        ):
            logger.warning("Indicator values unavailable for %s.", symbol)
            return {
                "symbol": symbol,
                "signal": "INVALID_DATA",
                "reason": "Indicator values unavailable",
            }

        signal = "WAIT"

        if prev_low < prev_lower_bb and current_rsi < self.rsi_oversold:
            if current_close > current_open and current_close > prev_close:
                signal = "LONG_REVERSION"

        elif prev_high > prev_upper_bb and current_rsi > self.rsi_overbought:
            if current_close < current_open and current_close < prev_close:
                signal = "SHORT_REVERSION"

        return {
            "symbol": symbol,
            "signal": signal,
            "mean_target": round(float(mid_bb), 2),
            "current_rsi": round(float(current_rsi), 2),
            "current_close": round(current_close, 2),
            "reversion_confirmed": signal != "WAIT",
        }
