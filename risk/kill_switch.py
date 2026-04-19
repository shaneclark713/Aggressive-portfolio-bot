from __future__ import annotations

import logging
from typing import Tuple

import pandas as pd

from strategies.indicators import adx, ema

logger = logging.getLogger("aggressive_portfolio_bot.risk.kill_switch")


class AntiFomoKillSwitch:
    def __init__(self, max_extension_pct: float = 0.04, adx_trend_threshold: float = 20.0):
        self.max_extension_pct = max_extension_pct
        self.adx_trend_threshold = adx_trend_threshold

    def check_trade_validity(self, df: pd.DataFrame, symbol: str, side: str) -> Tuple[bool, str]:
        required_cols = {"high", "low", "close"}
        if df.empty or not required_cols.issubset(df.columns):
            return False, "Invalid or incomplete market data"

        work = df[["high", "low", "close"]].dropna().copy()
        if len(work) < 30:
            return False, "Not enough candles for anti-FOMO validation"

        ema_9_series = ema(work["close"], 9).dropna()
        adx_14_series = adx(work, 14).dropna()

        if ema_9_series.empty or adx_14_series.empty:
            return False, "Indicators unavailable for anti-FOMO validation"

        close_price = float(work["close"].iloc[-1])
        ema_9 = float(ema_9_series.iloc[-1])
        adx_14 = float(adx_14_series.iloc[-1])

        extension_pct = abs(close_price - ema_9) / ema_9 if ema_9 > 0 else 0.0

        if extension_pct > self.max_extension_pct:
            return False, f"Price is too extended from EMA9 ({extension_pct:.2%})"

        if adx_14 < self.adx_trend_threshold:
            return False, f"Trend strength too weak (ADX {adx_14:.2f})"

        if side not in {"LONG", "SHORT"}:
            return False, "Invalid trade side"

        return True, "Trade passes anti-FOMO checks"
