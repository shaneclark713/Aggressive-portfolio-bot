from __future__ import annotations

import logging
from typing import Any, Dict, List

import pandas as pd

from config.filter_presets import FILTER_PRESETS
from config.universe import CORE_EQUITIES, CORE_FUTURES, DAY_TRADE_SETTINGS, SWING_TRADE_SETTINGS

logger = logging.getLogger("aggressive_portfolio_bot.data.universe_filter")


class UniverseFilter:
    def __init__(self, market_client):
        self.market_client = market_client
        self._last_watchlist_stats: Dict[str, Any] = {}

    def get_last_watchlist_stats(self) -> Dict[str, Any]:
        return dict(self._last_watchlist_stats)

    async def build_daily_watchlist(self) -> Dict[str, List[str]]:
        logger.info("Applying universe filters to build today's active watchlists...")
        day_trade_equities: List[str] = []
        swing_trade_equities: List[str] = []
        fetched = 0
        passed_day = 0
        passed_swing = 0
        errors = 0
        rejected: Dict[str, str] = {}
        metric_snapshot: Dict[str, Dict[str, float]] = {}
        descriptive_defaults = FILTER_PRESETS["day_trade_momentum"]["descriptive"]

        for symbol in CORE_EQUITIES:
            try:
                daily_df = await self.market_client.get_historical_data(
                    symbol=symbol,
                    multiplier=1,
                    timespan="day",
                )
            except Exception as exc:
                errors += 1
                rejected[symbol] = f"fetch_error: {exc}"
                logger.exception("[%s] Failed to fetch historical data: %s", symbol, exc)
                continue

            if daily_df.empty or len(daily_df) < 20:
                rejected[symbol] = "insufficient_daily_data"
                continue

            fetched += 1
            metrics = self._compute_metrics(daily_df, symbol)
            if not metrics:
                rejected[symbol] = "metric_calc_failed"
                continue

            try:
                premarket = await self.market_client.get_premarket_snapshot(symbol)
            except Exception:
                premarket = {
                    "premarket_volume": 0,
                    "premarket_gap_min_percent": 0.0,
                }

            try:
                details = await self.market_client.get_ticker_details(symbol)
            except Exception:
                details = {}

            float_value = (
                details.get("weighted_shares_outstanding")
                or details.get("share_class_shares_outstanding")
                or details.get("market_cap_float")
            )

            metrics["max_float"] = float(float_value) if float_value not in (None, "") else None
            metrics["premarket_volume"] = float(premarket.get("premarket_volume", 0) or 0)
            metrics["premarket_gap_min_percent"] = float(
                premarket.get("premarket_gap_min_percent", 0) or 0
            )

            metric_snapshot[symbol] = {
                "price": round(metrics["price"], 2),
                "relative_volume": round(metrics["relative_volume"], 2),
                "atr_pct": round(metrics["atr_pct"] * 100, 2),
                "gap_pct": round(metrics["gap_pct"] * 100, 2),
                "premarket_volume": round(metrics["premarket_volume"], 0),
                "premarket_gap_min_percent": round(metrics["premarket_gap_min_percent"], 2),
                "float_millions": round((metrics["max_float"] or 0) / 1_000_000, 2)
                if metrics["max_float"]
                else 0,
            }

            if self._passes_settings(metrics, DAY_TRADE_SETTINGS, descriptive_defaults):
                day_trade_equities.append(symbol)
                passed_day += 1
            else:
                rejected[symbol] = self._describe_rejection(
                    metrics,
                    DAY_TRADE_SETTINGS,
                    descriptive_defaults,
                )

            if self._passes_settings(metrics, SWING_TRADE_SETTINGS, descriptive_defaults):
                swing_trade_equities.append(symbol)
                passed_swing += 1

        self._last_watchlist_stats = {
            "symbols_considered": len(CORE_EQUITIES),
            "symbols_fetched": fetched,
            "day_trade_count": passed_day,
            "swing_trade_count": passed_swing,
            "errors": errors,
            "rejected_examples": dict(list(rejected.items())[:10]),
            "metric_snapshot": dict(list(metric_snapshot.items())[:10]),
        }

        logger.info(
            "Universe filter complete. day=%s swing=%s fetched=%s errors=%s",
            passed_day,
            passed_swing,
            fetched,
            errors,
        )

        return {
            "day_trade_equities": sorted(set(day_trade_equities)),
            "swing_trade_equities": sorted(set(swing_trade_equities)),
            "futures": CORE_FUTURES,
        }

    def _compute_metrics(self, df: pd.DataFrame, symbol: str) -> Dict[str, Any]:
        required_cols = {"open", "high", "low", "close", "volume"}
        if not required_cols.issubset(df.columns):
            logger.debug("[%s] Missing required columns for universe metrics.", symbol)
            return {}

        work_df = df[["open", "high", "low", "close", "volume"]].dropna().copy()
        if len(work_df) < 20:
            return {}

        atr_series = self._calculate_atr(work_df, period=14)
        if atr_series.empty:
            return {}

        latest = work_df.iloc[-1]
        avg_volume = float(work_df["volume"].tail(20).mean())
        avg_dollar_volume = float((work_df["close"] * work_df["volume"]).tail(20).mean())
        atr_pct = float(atr_series.iloc[-1] / latest["close"]) if latest["close"] else 0.0
        prior_close = float(work_df["close"].iloc[-2]) if len(work_df) >= 2 else float(latest["close"])
        gap_pct = abs(float(latest["open"] - prior_close) / prior_close) if prior_close else 0.0
        relative_volume = float(latest["volume"] / avg_volume) if avg_volume else 0.0

        return {
            "symbol": symbol,
            "price": float(latest["close"]),
            "avg_daily_volume": avg_volume,
            "avg_dollar_volume": avg_dollar_volume,
            "relative_volume": relative_volume,
            "atr_pct": atr_pct,
            "gap_pct": gap_pct,
        }

    def _passes_settings(
        self,
        metrics: Dict[str, Any],
        settings: Dict[str, Any],
        descriptive_defaults: Dict[str, Any],
    ) -> bool:
        max_float_limit = descriptive_defaults.get("max_float")
        if (
            max_float_limit
            and metrics.get("max_float") is not None
            and metrics["max_float"] > max_float_limit
        ):
            return False

        if metrics.get("premarket_volume", 0) < descriptive_defaults.get("min_premarket_vol", 0):
            return False

        if metrics.get("premarket_gap_min_percent", 0) < descriptive_defaults.get(
            "premarket_gap_min_percent", 0
        ):
            return False

        return (
            metrics["price"] >= settings["min_price"]
            and metrics["avg_daily_volume"] >= settings["min_avg_daily_volume"]
            and metrics["relative_volume"] >= settings["min_relative_volume"]
            and metrics["atr_pct"] >= settings["min_atr_pct"]
            and metrics["gap_pct"] <= settings["max_gap_pct"]
        )

    def _describe_rejection(
        self,
        metrics: Dict[str, Any],
        settings: Dict[str, Any],
        descriptive_defaults: Dict[str, Any],
    ) -> str:
        if (
            descriptive_defaults.get("max_float")
            and metrics.get("max_float") is not None
            and metrics["max_float"] > descriptive_defaults["max_float"]
        ):
            return "max_float"

        if metrics.get("premarket_volume", 0) < descriptive_defaults.get("min_premarket_vol", 0):
            return "premarket_volume"

        if metrics.get("premarket_gap_min_percent", 0) < descriptive_defaults.get(
            "premarket_gap_min_percent", 0
        ):
            return "premarket_gap_min_percent"

        return "failed_thresholds"

    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        high_low = df["high"] - df["low"]
        high_close = (df["high"] - df["close"].shift(1)).abs()
        low_close = (df["low"] - df["close"].shift(1)).abs()
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        return true_range.rolling(period).mean().dropna()
