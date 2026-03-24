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
        self._last_shortlist_metrics: Dict[str, Dict[str, Any]] = {}

    def get_last_watchlist_stats(self) -> Dict[str, Any]:
        return dict(self._last_watchlist_stats)

    def get_last_shortlist_metrics(self) -> Dict[str, Dict[str, Any]]:
        return dict(self._last_shortlist_metrics)

    async def build_daily_watchlist(self) -> Dict[str, List[str]]:
        logger.info("Applying lightweight universe filters to build today's active watchlists...")

        descriptive_defaults = FILTER_PRESETS["day_trade_momentum"]["descriptive"]
        day_trade_equities: List[str] = []
        swing_trade_equities: List[str] = []
        fetched = 0
        passed_day = 0
        passed_swing = 0
        errors = 0
        rate_limited = 0
        rejected: Dict[str, str] = {}
        metric_snapshot: Dict[str, Dict[str, float]] = {}

        for symbol in CORE_EQUITIES:
            try:
                daily_df = await self.market_client.get_historical_data(
                    symbol=symbol,
                    multiplier=1,
                    timespan="day",
                )
            except Exception as exc:
                errors += 1
                text = str(exc).lower()
                if "rate_limited" in text or "429" in text:
                    rate_limited += 1
                rejected[symbol] = f"fetch_error: {exc}"
                logger.warning("[%s] Lightweight universe fetch failed: %s", symbol, exc)
                continue

            if daily_df.empty or len(daily_df) < 20:
                rejected[symbol] = "insufficient_daily_data"
                continue

            fetched += 1
            metrics = self._compute_metrics(daily_df, symbol)
            if not metrics:
                rejected[symbol] = "metric_calc_failed"
                continue

            metric_snapshot[symbol] = {
                "price": round(metrics["price"], 2),
                "relative_volume": round(metrics["relative_volume"], 2),
                "atr_pct": round(metrics["atr_pct"] * 100, 2),
                "gap_pct": round(metrics["gap_pct"] * 100, 2),
            }

            if self._passes_lightweight_settings(metrics, DAY_TRADE_SETTINGS):
                day_trade_equities.append(symbol)
                passed_day += 1
            else:
                rejected[symbol] = "failed_lightweight_day_thresholds"

            if self._passes_lightweight_settings(metrics, SWING_TRADE_SETTINGS):
                swing_trade_equities.append(symbol)
                passed_swing += 1

        shortlist_cap = int(descriptive_defaults.get("shortlist_cap", 8) or 8)
        day_trade_equities = day_trade_equities[:shortlist_cap]
        swing_trade_equities = swing_trade_equities[: max(6, min(shortlist_cap, len(swing_trade_equities)))]

        self._last_watchlist_stats = {
            "symbols_considered": len(CORE_EQUITIES),
            "symbols_fetched": fetched,
            "day_trade_count": len(day_trade_equities),
            "swing_trade_count": len(swing_trade_equities),
            "passed_day_lightweight": passed_day,
            "passed_swing_lightweight": passed_swing,
            "errors": errors,
            "rate_limited": rate_limited,
            "rejected_examples": dict(list(rejected.items())[:10]),
            "metric_snapshot": dict(list(metric_snapshot.items())[:10]),
        }

        logger.info(
            "Lightweight universe complete. day_shortlist=%s swing_shortlist=%s fetched=%s errors=%s rate_limited=%s",
            len(day_trade_equities),
            len(swing_trade_equities),
            fetched,
            errors,
            rate_limited,
        )

        return {
            "day_trade_equities": sorted(set(day_trade_equities)),
            "swing_trade_equities": sorted(set(swing_trade_equities)),
            "futures": CORE_FUTURES,
        }

    async def enrich_symbol_for_entry(self, symbol: str) -> Dict[str, Any]:
        descriptive_defaults = FILTER_PRESETS["day_trade_momentum"]["descriptive"]
        result = {
            "symbol": symbol,
            "passes_heavy_filters": True,
            "rejection_reason": None,
            "max_float": None,
            "premarket_volume": 0.0,
            "premarket_gap_min_percent": 0.0,
        }

        try:
            premarket = await self.market_client.get_premarket_snapshot(symbol)
            result["premarket_volume"] = float(premarket.get("premarket_volume", 0) or 0)
            result["premarket_gap_min_percent"] = float(
                premarket.get("premarket_gap_min_percent", 0) or 0
            )
        except Exception as exc:
            result["passes_heavy_filters"] = False
            result["rejection_reason"] = f"premarket_fetch_failed: {exc}"
            self._last_shortlist_metrics[symbol] = result
            return result

        try:
            details = await self.market_client.get_ticker_details(symbol)
        except Exception:
            details = {}

        float_value = (
            details.get("weighted_shares_outstanding")
            or details.get("share_class_shares_outstanding")
            or details.get("market_cap_float")
        )
        result["max_float"] = float(float_value) if float_value not in (None, "") else None

        max_float_limit = descriptive_defaults.get("max_float")
        if (
            max_float_limit
            and result["max_float"] is not None
            and result["max_float"] > max_float_limit
        ):
            result["passes_heavy_filters"] = False
            result["rejection_reason"] = "max_float"
        elif result["premarket_volume"] < descriptive_defaults.get("min_premarket_vol", 0):
            result["passes_heavy_filters"] = False
            result["rejection_reason"] = "premarket_volume"
        elif result["premarket_gap_min_percent"] < descriptive_defaults.get(
            "premarket_gap_min_percent", 0
        ):
            result["passes_heavy_filters"] = False
            result["rejection_reason"] = "premarket_gap_min_percent"

        self._last_shortlist_metrics[symbol] = result
        return result

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

    def _passes_lightweight_settings(self, metrics: Dict[str, Any], settings: Dict[str, Any]) -> bool:
        return (
            metrics["price"] >= settings["min_price"]
            and metrics["avg_daily_volume"] >= settings["min_avg_daily_volume"]
            and metrics["relative_volume"] >= settings["min_relative_volume"]
            and metrics["atr_pct"] >= settings["min_atr_pct"]
            and metrics["gap_pct"] <= settings["max_gap_pct"]
        )

    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        high_low = df["high"] - df["low"]
        high_close = (df["high"] - df["close"].shift(1)).abs()
        low_close = (df["low"] - df["close"].shift(1)).abs()
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        return true_range.rolling(period).mean().dropna()
