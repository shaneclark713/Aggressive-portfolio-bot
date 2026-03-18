import logging
from typing import Dict, Any, List

import pandas as pd

logger = logging.getLogger("aggressive_portfolio_bot.strategies.trend_following")


class TrendFollowingStrategy:
    def __init__(self, adx_threshold: int = 25):
        self.adx_threshold = adx_threshold

    def _ema(self, series: pd.Series, length: int) -> pd.Series:
        return series.ewm(span=length, adjust=False).mean()

    def _sma(self, series: pd.Series, length: int) -> pd.Series:
        return series.rolling(window=length, min_periods=length).mean()

    def _adx(self, df: pd.DataFrame, length: int = 14) -> pd.Series:
        high = df["high"]
        low = df["low"]
        close = df["close"]

        up_move = high.diff()
        down_move = -low.diff()

        plus_dm = pd.Series(
            [up if (pd.notna(up) and pd.notna(down) and up > down and up > 0) else 0.0
             for up, down in zip(up_move, down_move)],
            index=df.index,
            dtype="float64",
        )
        minus_dm = pd.Series(
            [down if (pd.notna(up) and pd.notna(down) and down > up and down > 0) else 0.0
             for up, down in zip(up_move, down_move)],
            index=df.index,
            dtype="float64",
        )

        prev_close = close.shift(1)
        tr = pd.concat(
            [
                high - low,
                (high - prev_close).abs(),
                (low - prev_close).abs(),
            ],
            axis=1,
        ).max(axis=1)

        atr = tr.rolling(window=length, min_periods=length).mean()
        plus_di = 100 * (plus_dm.rolling(window=length, min_periods=length).mean() / atr)
        minus_di = 100 * (minus_dm.rolling(window=length, min_periods=length).mean() / atr)

        dx = ((plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, pd.NA)) * 100
        adx = dx.rolling(window=length, min_periods=length).mean()
        return adx

    def analyze(self, df: pd.DataFrame, symbol: str) -> Dict[str, Any]:
        required_cols: List[str] = ["high", "low", "close"]
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            logger.warning("Missing required columns for %s: %s", symbol, missing_cols)
            return {
                "symbol": symbol,
                "signal": "INVALID_DATA",
                "reason": f"Missing columns: {missing_cols}",
            }

        clean_df = df[required_cols].dropna().copy()
        if len(clean_df) < 50:
            return {
                "symbol": symbol,
                "signal": "INSUFFICIENT_DATA",
            }

        clean_df["EMA_9"] = self._ema(clean_df["close"], 9)
        clean_df["SMA_21"] = self._sma(clean_df["close"], 21)
        clean_df["ADX_14"] = self._adx(clean_df, 14)

        latest = clean_df.iloc[-1]

        close_price = float(latest["close"])
        ema_9 = latest.get("EMA_9")
        sma_21 = latest.get("SMA_21")
        adx_14 = latest.get("ADX_14")

        if pd.isna(ema_9) or pd.isna(sma_21) or pd.isna(adx_14):
            logger.warning("Indicator values unavailable for %s.", symbol)
            return {
                "symbol": symbol,
                "signal": "INVALID_DATA",
                "reason": "Indicator values unavailable",
            }

        signal = "WAIT"

        if adx_14 > self.adx_threshold:
            if ema_9 > sma_21 and close_price > ema_9:
                signal = "LONG_TREND"
            elif ema_9 < sma_21 and close_price < ema_9:
                signal = "SHORT_TREND"

        return {
            "symbol": symbol,
            "signal": signal,
            "adx_strength": round(float(adx_14), 2),
            "ema_9": round(float(ema_9), 2),
            "sma_21": round(float(sma_21), 2),
            "close_price": round(close_price, 2),
        }
