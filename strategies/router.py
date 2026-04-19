from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import pandas as pd

from .breakout_box import BreakoutBoxStrategy
from .divergence import DivergenceStrategy
from .indicators import atr, percent_change
from .market_regime import MarketRegimeClassifier
from .mean_reversion import MeanReversionStrategy
from .trend_following import TrendFollowingStrategy
from risk.kill_switch import AntiFomoKillSwitch
from risk.risk_engine import RiskEngine

logger = logging.getLogger("aggressive_portfolio_bot.strategies.router")


class StrategyRouter:
    def __init__(self, strategy_states: Optional[Dict[str, bool]] = None):
        self.strategy_states = strategy_states or {}
        self.strategies = [
            ("Divergence", DivergenceStrategy()),
            ("Breakout Box", BreakoutBoxStrategy()),
            ("Trend Following", TrendFollowingStrategy()),
            ("Mean Reversion", MeanReversionStrategy()),
        ]
        self.kill_switch = AntiFomoKillSwitch()
        self.risk_engine = RiskEngine(min_rr_ratio=2.0, atr_multiplier_sl=1.0)
        self.market_regime = MarketRegimeClassifier()

    def _is_enabled(self, strategy_name: str) -> bool:
        return bool(self.strategy_states.get(strategy_name, True))

    def _classify_trade_horizon(self, strategy_name: str, regime: str) -> str:
        if strategy_name == "Mean Reversion":
            return "DAY_TRADE"
        if strategy_name == "Trend Following":
            return "SWING_TRADE"
        if strategy_name == "Divergence" and regime in {"RANGE", "TRANSITION"}:
            return "DAY_TRADE"
        if strategy_name == "Breakout Box" and regime.startswith("TREND"):
            return "DAY_TRADE"
        return "SWING_TRADE"

    def _entry_zone(self, entry_price: float, side: str, atr_value: float) -> list[float]:
        buffer_amt = atr_value * 0.10
        if side == "LONG":
            return [round(entry_price - buffer_amt, 2), round(entry_price + buffer_amt, 2)]
        return [round(entry_price + buffer_amt, 2), round(entry_price - buffer_amt, 2)]

    def evaluate_ticker(self, symbol: str, df: pd.DataFrame) -> Optional[Dict[str, Any]]:
        required = {"open", "high", "low", "close", "volume"}
        if df.empty or not required.issubset(df.columns):
            return None

        work_df = df[list(required)].dropna().copy()
        if len(work_df) < 50:
            return None

        regime = self.market_regime.classify(work_df)
        selected_setup: Optional[Dict[str, Any]] = None
        selected_strategy_name: Optional[str] = None

        for strategy_name, strategy in self.strategies:
            if not self._is_enabled(strategy_name):
                continue
            result = strategy.analyze(work_df, symbol)
            signal = result.get("signal", "WAIT")
            if signal.startswith("LONG_") or signal.startswith("SHORT_"):
                selected_setup = result
                selected_strategy_name = strategy_name
                break

        if not selected_setup or not selected_strategy_name:
            return None

        side = "LONG" if selected_setup["signal"].startswith("LONG_") else "SHORT"

        is_safe, kill_switch_reason = self.kill_switch.check_trade_validity(work_df, symbol, side)
        if not is_safe:
            logger.info("[%s] Blocked by kill switch: %s", symbol, kill_switch_reason)
            return None

        atr_series = atr(work_df[["high", "low", "close"]], 14).dropna()
        if atr_series.empty:
            return None

        atr_value = float(atr_series.iloc[-1])
        entry_price = float(work_df["close"].iloc[-1])
        recent_window = work_df.iloc[-21:-1]
        recent_swing_high = float(recent_window["high"].max())
        recent_swing_low = float(recent_window["low"].min())

        risk_data = self.risk_engine.calculate_trade_parameters(
            symbol=symbol,
            entry_price=entry_price,
            side=side,
            atr=atr_value,
            recent_swing_high=recent_swing_high,
            recent_swing_low=recent_swing_low,
        )
        if not risk_data.get("is_valid", False):
            return None

        trade_horizon = self._classify_trade_horizon(selected_strategy_name, regime)
        trigger_reasons = selected_setup.get("trigger_reasons", [])
        confidence = int(selected_setup.get("confidence", 0))
        metrics = dict(selected_setup.get("metrics", {}))

        move_5 = percent_change(work_df["close"], periods=min(5, len(work_df) - 1)).iloc[-1]
        volume_ratio_now = float(work_df["volume"].iloc[-1] / work_df["volume"].tail(20).mean())

        reward = float(risk_data["reward"])
        second_target = entry_price + (reward * 1.5) if side == "LONG" else entry_price - (reward * 1.5)
        targets = [round(float(risk_data["take_profit"]), 2), round(float(second_target), 2)]

        payload = {
            "symbol": symbol,
            "strategy": selected_strategy_name,
            "signal": selected_setup["signal"],
            "side": side,
            "regime": regime,
            "trade_horizon": trade_horizon,
            "holding_style": "Intraday" if trade_horizon == "DAY_TRADE" else "Multi-Day",
            "entry_price": round(float(risk_data["entry_price"]), 2),
            "entry_zone": self._entry_zone(entry_price, side, atr_value),
            "stop_loss": round(float(risk_data["stop_loss"]), 2),
            "take_profit": round(float(risk_data["take_profit"]), 2),
            "targets": targets,
            "risk_per_share": round(float(risk_data["risk"]), 2),
            "reward_per_share": round(float(risk_data["reward"]), 2),
            "rr_ratio": round(float(risk_data["actual_rr"]), 2),
            "confidence": confidence,
            "trigger_reasons": trigger_reasons,
            "filter_pass_summary": {"kill_switch": True, "risk_engine": True, "strategy_enabled": True},
            "metrics": {
                **metrics,
                "atr_14": round(atr_value, 2),
                "atr_pct": round((atr_value / entry_price) * 100, 2),
                "volume_ratio": round(volume_ratio_now, 2),
                "move_last_window_pct": round(float(move_5), 2),
            },
            "notes": selected_setup.get("metadata", {}),
        }

        if selected_strategy_name == "Mean Reversion" and "mean_target" in metrics:
            payload["take_profit"] = round(float(metrics["mean_target"]), 2)
            payload["targets"][0] = payload["take_profit"]

        return payload
