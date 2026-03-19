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
        low = df
