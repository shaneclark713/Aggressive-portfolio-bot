import logging
from typing import Dict, Any, Optional

import pandas as pd

from .breakout_box import BreakoutBoxStrategy
from .trend_following import TrendFollowingStrategy
from .divergence import DivergenceStrategy
from .mean_reversion import MeanReversionStrategy
from aggressive_portfolio_bot.risk.kill_switch import AntiFomoKillSwitch
from aggressive_portfolio_bot.risk.risk_engine import RiskEngine

logger = logging.getLogger("aggressive_portfolio_bot.strategies.router")


class StrategyRouter:
    def __init__(self):
        self.strategies = {
            "Divergence": DivergenceStrategy(),
            "Breakout Box": BreakoutBoxStrategy(),
            "Trend Following": TrendFollowingStrategy(),
            "Mean Reversion": MeanReversionStrategy(),
        }

        self.kill_switch = AntiFomoKillSwitch()
        self.risk_engine = RiskEngine(min_rr_ratio=2.0, atr_multiplier_sl=1.0)

    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        prev_close = df["close"].shift(1)
        tr = pd.concat(
            [
                df["high"] - df["low"],
                (df["high"] - prev_close).abs(),
                (df["low"] - prev_close).abs(),
            ],
            axis=1,
        ).max(axis=1)
        return tr.rolling(window=period, min_periods=period).mean()

    def _classify_trade_horizon(
        self,
        strategy_name: str,
        entry_price: float,
        take_profit: float,
        atr: float,
        rr_ratio: float,
    ) -> str:
        target_distance = abs(take_profit - entry_price)
        atr_multiple_to_target = target_distance / atr if atr > 0 else 0.0

        if strategy_name == "Mean Reversion":
            return "DAY_TRADE"

        if strategy_name == "Trend Following":
            return "SWING_TRADE"

        if strategy_name == "Breakout Box":
            if atr_multiple_to_target <= 1.5 and rr_ratio <= 2.5:
                return "DAY_TRADE"
            return "SWING_TRADE"

        if strategy_name == "Divergence":
            if atr_multiple_to_target <= 1.25:
                return "DAY_TRADE"
            return "SWING_TRADE"

        return "DAY_TRADE"

    def evaluate_ticker(self, symbol: str, df: pd.DataFrame) -> Optional[Dict[str, Any]]:
        required_cols = {"open", "high", "low", "close", "volume"}
        if df.empty:
