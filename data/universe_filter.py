from __future__ import annotations

import logging
from typing import Any, Dict, List

import pandas as pd

from config.universe import CORE_FUTURES

logger = logging.getLogger("aggressive_portfolio_bot.data.universe_filter")


class UniverseFilter:
    PROFILE_MAP = {
        "market": "overall",
        "scan": "overall",
        "overall": "overall",
        "premarket": "premarket",
        "midday": "midday",
        "overnight": "overnight",
        "swing": "overnight",
    }

    def __init__(self, market_client, config_service, discovery_service):
        self.market_client = market_client
        self.config_service = config_service
        self.discovery_service = discovery_service
        self._last_watchlist_stats: Dict[str, Any] = {}
        self._last_shortlist_metrics: Dict[str, Dict[str, Any]] = {}
        self._last_passers: List[Dict[str, Any]] = []

    def get_last_watchlist_stats(self) -> Dict[str, Any]:
        return dict(self._last_watchlist_stats)

    def get_last_shortlist_metrics(self) -> Dict[str, Dict[str, Any]]:
        return dict(self._last_shortlist_metrics)

    def get_last_passers(self) -> List[Dict[str, Any]]:
        return list(self._last_passers)

    def _profile_for_scan(self, scan_type: str) -> str:
        return self.PROFILE_MAP.get(scan_type, "overall")

    def _filters_for_scan(self, scan_type: str) -> Dict[str, Dict[str, Any]]:
        return self.config_service.resolve_filters(profile=self._profile_for_scan(scan_type))

    async def build_daily_watchlist(self, scan_type: str = "market", force_refresh: bool = False) -> Dict[str, List[str]]:
        profile = self._profile_for_scan(scan_type)
        filters = self._filters_for_scan(scan_type)
        descriptive = filters["descriptive"]
        technical = filters["technical"]
        candidate_rows = await self.discovery_service.get_candidate_rows(scan_type, force_refresh=force_refresh)
        discovery_status = await self.discovery_service.snapshot_status(profile)
        discovery_count = len(candidate_rows)
        shortlisted = []
        swing_trade_equities = []
        fetched = passed_day = passed_swing = errors = rate_limited = 0
        rejected = {}
        rejection_counts = {}
        metric_snapshot = {}

        def reject(symbol: str, reason: str) -> None:
            rejected[symbol] = reason
            rejection_counts[reason] = rejection_counts.get(reason, 0) + 1
        self._last_passers = []
        shortlist_cap = int(descriptive.get("shortlist_cap", 8) or 8)

        for row in candidate_rows:
            symbol = row["symbol"]
            try:
                daily_df = await self.market_client.get_historical_data(symbol=symbol, multiplier=1, timespan="day")
            except Exception as exc:
                errors += 1
                if "rate_limited" in str(exc).lower() or "429" in str(exc):
                    rate_limited += 1
                    reject(symbol, "rate_limited")
                else:
                    reject(symbol, f"fetch_error: {exc.__class__.__name__}")
                logger.warning("[%s] Dynamic universe fetch failed: %s", symbol, exc)
                continue
            if daily_df.empty:
                reject(symbol, "empty_daily_data")
                continue
            if len(daily_df) < 20:
                reject(symbol, "insufficient_daily_data")
                continue
            fetched += 1
            metrics = self._compute_metrics(daily_df, symbol)
            if not metrics:
                reject(symbol, "metric_calc_failed")
                continue
            metric_snapshot[symbol] = {
                "price": round(metrics["price"], 2),
                "relative_volume": round(metrics["relative_volume"], 2),
                "atr_pct": round(metrics["atr_pct"] * 100, 2),
                "gap_pct": round(metrics["gap_pct"] * 100, 2),
                "day_dollar_volume": round(row.get("day_dollar_volume", 0), 2),
            }
            day_reasons = self._lightweight_rejection_reasons(metrics, descriptive, technical)
            if not day_reasons:
                shortlisted.append(symbol)
                passed_day += 1
                self._last_passers.append({"symbol": symbol, **metric_snapshot[symbol]})
            else:
                reject(symbol, ",".join(day_reasons[:3]))
            if self._passes_lightweight_filters(metrics, descriptive, technical, swing=True):
                swing_trade_equities.append(symbol)
                passed_swing += 1
            if len(shortlisted) >= shortlist_cap:
                break

        swing_trade_equities = swing_trade_equities[: max(6, min(shortlist_cap, len(swing_trade_equities)))]
        if discovery_count == 0:
            snapshot_reasons = discovery_status.get("skip_reasons") or {}
            if isinstance(snapshot_reasons, dict):
                for reason, count in snapshot_reasons.items():
                    rejection_counts.setdefault(reason, count)
            rejected.setdefault("discovery", "no_candidate_rows_after_snapshot_filters")

        self._last_watchlist_stats = {
            "scan_type": scan_type,
            "profile": profile,
            "snapshot_raw_count": discovery_status.get("raw_count", "n/a"),
            "snapshot_row_count": discovery_status.get("row_count", 0),
            "snapshot_skipped": discovery_status.get("skipped", 0),
            "snapshot_skip_reasons": discovery_status.get("skip_reasons", {}),
            "symbols_considered": discovery_count,
            "symbols_fetched": fetched,
            "day_trade_count": len(shortlisted),
            "swing_trade_count": len(swing_trade_equities),
            "passed_day_lightweight": passed_day,
            "passed_swing_lightweight": passed_swing,
            "errors": errors,
            "rate_limited": rate_limited,
            "rejected_examples": dict(list(rejected.items())[:10]),
            "rejection_counts": dict(sorted(rejection_counts.items(), key=lambda item: (-item[1], item[0]))),
            "metric_snapshot": dict(list(metric_snapshot.items())[:10]),
            "source": discovery_status.get("source", "dynamic_market_snapshot"),
        }
        return {"day_trade_equities": sorted(set(shortlisted)), "swing_trade_equities": sorted(set(swing_trade_equities)), "futures": CORE_FUTURES}

    async def enrich_symbol_for_entry(self, symbol: str, scan_type: str = "market") -> Dict[str, Any]:
        descriptive = self._filters_for_scan(scan_type)["descriptive"]
        result = {"symbol": symbol, "scan_type": scan_type, "passes_heavy_filters": True, "rejection_reason": None, "max_float": None, "premarket_volume": 0.0, "premarket_gap_min_percent": 0.0, "premarket_data_unavailable": False}
        try:
            details = await self.market_client.get_ticker_details(symbol)
        except Exception:
            details = {}
        float_value = details.get("weighted_shares_outstanding") or details.get("share_class_shares_outstanding") or details.get("market_cap_float")
        result["max_float"] = float(float_value) if float_value not in (None, "") else None
        max_float_limit = descriptive.get("max_float")
        if max_float_limit and result["max_float"] is not None and result["max_float"] > max_float_limit:
            result["passes_heavy_filters"] = False
            result["rejection_reason"] = "max_float"
            self._last_shortlist_metrics[symbol] = result
            return result
        if scan_type == "premarket":
            try:
                premarket = await self.market_client.get_premarket_snapshot(symbol)
                result["premarket_volume"] = float(premarket.get("premarket_volume", 0) or 0)
                result["premarket_gap_min_percent"] = float(premarket.get("premarket_gap_min_percent", 0) or 0)
            except Exception as exc:
                result["passes_heavy_filters"] = False
                result["rejection_reason"] = f"premarket_fetch_failed: {exc}"
                result["premarket_data_unavailable"] = True
                self._last_shortlist_metrics[symbol] = result
                return result
            if result["premarket_volume"] < descriptive.get("min_premarket_vol", 0):
                result["passes_heavy_filters"] = False
                result["rejection_reason"] = "premarket_volume"
            elif result["premarket_gap_min_percent"] < descriptive.get("premarket_gap_min_percent", 0):
                result["passes_heavy_filters"] = False
                result["rejection_reason"] = "premarket_gap_min_percent"
        self._last_shortlist_metrics[symbol] = result
        return result

    def _compute_metrics(self, df: pd.DataFrame, symbol: str) -> Dict[str, Any]:
        if not {"open", "high", "low", "close", "volume"}.issubset(df.columns):
            return {}
        work_df = df[["open", "high", "low", "close", "volume"]].dropna().copy()
        if len(work_df) < 20:
            return {}
        atr_series = self._calculate_atr(work_df, 14)
        if atr_series.empty:
            return {}
        latest = work_df.iloc[-1]
        avg_volume = float(work_df["volume"].tail(20).mean())
        avg_dollar = float((work_df["close"] * work_df["volume"]).tail(20).mean())
        atr_pct = float(atr_series.iloc[-1] / latest["close"]) if latest["close"] else 0.0
        prior_close = float(work_df["close"].iloc[-2]) if len(work_df) >= 2 else float(latest["close"])
        gap_pct = abs(float(latest["open"] - prior_close) / prior_close) if prior_close else 0.0
        rel = float(latest["volume"] / avg_volume) if avg_volume else 0.0
        return {"symbol": symbol, "price": float(latest["close"]), "avg_daily_volume": avg_volume, "avg_dollar_volume": avg_dollar, "relative_volume": rel, "atr_pct": atr_pct, "gap_pct": gap_pct}

    def _passes_lightweight_filters(self, metrics: Dict[str, Any], descriptive: Dict[str, Any], technical: Dict[str, Any], swing: bool = False) -> bool:
        max_gap_pct = float(technical.get("premarket_gap_max_pct", 12.0)) / 100.0
        return (
            metrics["price"] >= float(descriptive.get("price_min", 0))
            and metrics["avg_daily_volume"] >= float(descriptive.get("avg_daily_volume_min", 0))
            and metrics["avg_dollar_volume"] >= float(descriptive.get("avg_dollar_volume_min", 0))
            and metrics["relative_volume"] >= float(technical.get("volume_vs_average_min_ratio", 1.0))
            and metrics["atr_pct"] >= float(technical.get("atr_min_pct", 0))
            and metrics["gap_pct"] <= max_gap_pct
        )

    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        high_low = df["high"] - df["low"]
        high_close = (df["high"] - df["close"].shift(1)).abs()
        low_close = (df["low"] - df["close"].shift(1)).abs()
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        return true_range.rolling(period).mean().dropna()
