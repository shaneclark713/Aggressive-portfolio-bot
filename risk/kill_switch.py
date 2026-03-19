import logging
from typing import Tuple

import pandas as pd

logger = logging.getLogger("aggressive_portfolio_bot.risk.kill_switch")


class AntiFomoKillSwitch:
    def __init__(
        self,
        max_extension_pct: float = 0.04,
        adx_trend_threshold: float = 20.0,
    ):
        self.max_extension_pct = max_extension_pct
        self.adx_trend_threshold = adx_trend_threshold

    def _ema(self, series: pd.Series, length: int) -> pd.Series:
        return series.ewm(span=length, adjust=False).mean()

    def _adx(self, df: pd.DataFrame, length: int = 14) -> pd.Series:
        high = df["high"]
        low = df["low"]
        close = df["close"]

        up_move = high.diff()
        down_move = -low.diff()

        plus_dm = pd.Series(
            [
                up if pd.notna(up) and pd.notna(down) and up > down and up > 0 else 0.0
                for up, down in zip(up_move, down_move)
            ],
            index=df.index,
            dtype="float64",
        )

        minus_dm = pd.Series(
            [
                down if pd.notna(up) and pd.notna(down) and down > up and down > 0 else 0.0
                for up, down in zip(up_move, down_move)
            ],
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

    def check_trade_validity(self, df: pd.DataFrame, symbol: str, side: str) -> Tuple[bool, str]:
        required_cols = {"high", "low", "close"}
        if df.empty or not required_cols.issubset(df.columns):
            return False, "Invalid or incomplete market data"

        work = df[["high", "low", "close"]].dropna().copy()
        if len(work) < 30:
            return False, "Not enough candles for anti-FOMO validation"

        work["EMA_9"] = self._ema(work["close"], 9)
        work["ADX_14"] = self._adx(work, 14)

        latest = work.iloc[-1]
        close_price = float(latest["close"])
        ema_9 = latest.get("EMA_9")
        adx_14 = latest.get("ADX_14")

        if pd.isna(ema_9) or pd.isna(adx_14):
            return False, "Indicators unavailable for anti-FOMO validation"

        extension_pct = abs(close_price - float(ema_9)) / float(ema_9) if float(ema_9) > 0 else 0.0

        if extension_pct > self.max_extension_pct:
            return False, f"Price is too extended from EMA9 ({extension_pct:.2%})"

        if float(adx_14) < self.adx_trend_threshold:
            return False, f"Trend strength too weak (ADX {float(adx_14):.2f})"

        if side not in {"LONG", "SHORT"}:
            return False, "Invalid trade side"

        return True, "Trade passes anti-FOMO checks"
