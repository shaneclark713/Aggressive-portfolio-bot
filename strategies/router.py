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
            logger.debug("[%s] DataFrame is empty.", symbol)
            return None

        if not required_cols.issubset(df.columns):
            missing = sorted(required_cols - set(df.columns))
            logger.warning("[%s] Missing required columns: %s", symbol, missing)
            return None

        work_df = df[list(required_cols)].dropna().copy()
        if len(work_df) < 50:
            logger.debug("[%s] Not enough clean data to evaluate.", symbol)
            return None

        detected_signal = "WAIT"
        winning_strategy_name: Optional[str] = None
        setup_data: Dict[str, Any] = {}

        for name, strategy_module in self.strategies.items():
            try:
                result = strategy_module.analyze(work_df, symbol)
            except Exception as e:
                logger.exception("[%s] Strategy '%s' failed: %s", symbol, name, e)
                continue

            signal = result.get("signal", "WAIT")
            if signal.startswith("LONG_") or signal.startswith("SHORT_"):
                detected_signal = signal
                winning_strategy_name = name
                setup_data = result
                break

        if detected_signal == "WAIT" or winning_strategy_name is None:
            logger.debug("[%s] No valid strategy trigger found.", symbol)
            return None

        side = "LONG" if detected_signal.startswith("LONG_") else "SHORT"
        logger.info("[%s] Triggered %s via %s. Running protections...", symbol, side, winning_strategy_name)

        try:
            is_safe, fomo_reason = self.kill_switch.check_trade_validity(work_df, symbol, side)
        except Exception as e:
            logger.exception("[%s] Kill switch failed: %s", symbol, e)
            return None

        if not is_safe:
            logger.warning("[%s] %s blocked by Kill Switch: %s", symbol, winning_strategy_name, fomo_reason)
            return None

        risk_df = work_df.copy()
        atr_series = self._calculate_atr(risk_df, period=14)

        if atr_series.dropna().empty:
            logger.warning("[%s] Invalid ATR value for risk calculation.", symbol)
            return None

        latest = risk_df.iloc[-1]
        entry_price = float(latest["close"])
        current_atr = float(atr_series.dropna().iloc[-1])

        prior_structure = risk_df.iloc[-21:-1]
        if prior_structure.empty:
            logger.warning("[%s] Not enough prior candles for structural levels.", symbol)
            return None

        recent_swing_high = float(prior_structure["high"].max())
        recent_swing_low = float(prior_structure["low"].min())

        try:
            risk_data = self.risk_engine.calculate_trade_parameters(
                symbol=symbol,
                entry_price=entry_price,
                side=side,
                atr=current_atr,
                recent_swing_high=recent_swing_high,
                recent_swing_low=recent_swing_low,
            )
        except Exception as e:
            logger.exception("[%s] Risk engine failed: %s", symbol, e)
            return None

        if not risk_data.get("is_valid", False):
            logger.info(
                "[%s] %s blocked by Risk Engine: %s",
                symbol,
                winning_strategy_name,
                risk_data.get("reason", "Unknown reason"),
            )
            return None

        final_payload: Dict[str, Any] = {
            "symbol": symbol,
            "strategy": winning_strategy_name,
            "signal": detected_signal,
            "side": side,
            "entry_price": risk_data["entry_price"],
            "stop_loss": risk_data["stop_loss"],
            "take_profit": risk_data["take_profit"],
            "risk_per_share": risk_data["risk"],
            "reward_per_share": risk_data["reward"],
            "rr_ratio": risk_data["actual_rr"],
        }

        if "box_high" in setup_data:
            final_payload["box_high"] = setup_data["box_high"]
        if "box_low" in setup_data:
            final_payload["box_low"] = setup_data["box_low"]
        if "mean_target" in setup_data:
            final_payload["mean_target"] = setup_data["mean_target"]

        if winning_strategy_name == "Mean Reversion" and "mean_target" in setup_data:
            try:
                mean_target = float(setup_data["mean_target"])
                if side == "LONG" and mean_target > final_payload["entry_price"]:
                    final_payload["take_profit"] = round(mean_target, 2)
                    final_payload["reward_per_share"] = round(
                        mean_target - final_payload["entry_price"], 2
                    )
                elif side == "SHORT" and mean_target < final_payload["entry_price"]:
                    final_payload["take_profit"] = round(mean_target, 2)
                    final_payload["reward_per_share"] = round(
                        final_payload["entry_price"] - mean_target, 2
                    )

                risk_per_share = float(final_payload["risk_per_share"])
                reward_per_share = float(final_payload["reward_per_share"])
                if risk_per_share > 0:
                    final_payload["rr_ratio"] = round(reward_per_share / risk_per_share, 2)

            except (TypeError, ValueError):
                logger.warning("[%s] Invalid mean_target value in setup data.", symbol)

        trade_horizon = self._classify_trade_horizon(
            strategy_name=winning_strategy_name,
            entry_price=float(final_payload["entry_price"]),
            take_profit=float(final_payload["take_profit"]),
            atr=current_atr,
            rr_ratio=float(final_payload["rr_ratio"]),
        )

        final_payload["trade_horizon"] = trade_horizon
        final_payload["holding_style"] = "Intraday" if trade_horizon == "DAY_TRADE" else "Multi-Day"

        logger.info(
            "[%s] SUCCESS: Valid %s payload generated as %s.",
            symbol,
            winning_strategy_name,
            trade_horizon,
        )
        return final_payload
