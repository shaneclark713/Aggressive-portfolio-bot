from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List

from config.symbols import benchmark_for_symbol

logger = logging.getLogger("aggressive_portfolio_bot.data.scanners")


class ScannerService:
    def __init__(self, market_client, universe_filter, router, news_client=None, econ_client=None):
        self.market_client = market_client
        self.universe_filter = universe_filter
        self.router = router
        self.news_client = news_client
        self.econ_client = econ_client
        self._last_scan_stats: Dict[str, Any] = {}

    def get_last_scan_stats(self) -> Dict[str, Any]:
        return dict(self._last_scan_stats)

    def _compact_error(self, exc: Exception) -> str:
        text = str(exc).lower()
        if "429" in text or "rate_limited" in text or "too many requests" in text:
            return "rate_limited"
        if "timeout" in text:
            return "timeout"
        return exc.__class__.__name__

    async def _scan_symbols(self, symbols: list[str], multiplier: int, timespan: str, scan_label: str, scan_type: str) -> List[Dict[str, Any]]:
        candidates: List[Dict[str, Any]] = []
        errors = evaluated = qualified = rate_limited = 0
        heavy_rejection_count = empty_data_count = no_signal_count = 0
        top_symbols: List[str] = []
        error_examples: List[str] = []
        heavy_rejections: List[str] = []
        rejection_counts: Dict[str, int] = {}
        scan_time = datetime.now(timezone.utc).isoformat()
        today = date.today().isoformat()
        start = (date.today() - timedelta(days=3)).isoformat()

        def count_rejection(reason: str) -> None:
            rejection_counts[reason] = rejection_counts.get(reason, 0) + 1

        for index, symbol in enumerate(symbols):
            try:
                heavy = await self.universe_filter.enrich_symbol_for_entry(symbol, scan_type=scan_type)
                if not heavy.get("passes_heavy_filters", False):
                    reason = str(heavy.get("rejection_reason") or "heavy_filter_failed")
                    heavy_rejection_count += 1
                    count_rejection(reason)
                    heavy_rejections.append(f"{symbol}: {reason}")
                    continue

                df = await self.market_client.get_historical_data(symbol=symbol, multiplier=multiplier, timespan=timespan)
                if df.empty:
                    empty_data_count += 1
                    count_rejection("empty_market_data")
                    error_examples.append(f"{symbol}: empty_market_data")
                    continue

                evaluated += 1
                payload = self.router.evaluate_ticker(symbol, df)
                if not payload:
                    no_signal_count += 1
                    count_rejection("no_strategy_signal")
                    error_examples.append(f"{symbol}: no_strategy_signal")
                    continue

                symbol_news_count = 0
                catalyst_headlines: List[str] = []
                if self.news_client is not None:
                    try:
                        symbol_news = await self.news_client.fetch_ticker_news(symbol, start_date=start, end_date=today)
                        symbol_news_count = len(symbol_news)
                        catalyst_headlines = self.news_client.summarize_headlines(symbol_news, limit=3)
                    except Exception:
                        pass

                payload.update({
                    "benchmark": benchmark_for_symbol(symbol),
                    "scan_label": scan_label,
                    "scan_type": scan_type,
                    "scan_timestamp_utc": scan_time,
                    "news_count": symbol_news_count,
                    "catalyst_headlines": catalyst_headlines,
                    "premarket_volume": heavy.get("premarket_volume", 0),
                    "premarket_gap_min_percent": heavy.get("premarket_gap_min_percent", 0),
                    "max_float": heavy.get("max_float"),
                })
                candidates.append(payload)
                qualified += 1
                top_symbols.append(symbol)

            except Exception as exc:
                errors += 1
                compact = self._compact_error(exc)
                if compact == "rate_limited":
                    rate_limited += 1
                count_rejection(compact)
                error_examples.append(f"{symbol}: {compact}")
                logger.warning("Scanner failed for %s during %s: %s", symbol, scan_label, compact)

            finally:
                if index < len(symbols) - 1:
                    await asyncio.sleep(0.5)

        watchlist_stats = self.universe_filter.get_last_watchlist_stats()
        combined_examples = (error_examples + heavy_rejections)[:10]
        self._last_scan_stats = {
            "scan_label": scan_label,
            "scan_type": scan_type,
            "profile": watchlist_stats.get("profile", scan_type),
            "scan_timestamp_utc": scan_time,
            "universe_loaded": watchlist_stats.get("symbols_considered", len(symbols)),
            "discovery_candidates": watchlist_stats.get("symbols_considered", len(symbols)),
            "passed_universe_filters": len(symbols),
            "lightweight_watchlist_count": len(symbols),
            "symbols_fetched": watchlist_stats.get("symbols_fetched", 0),
            "evaluated": evaluated,
            "symbols_evaluated": evaluated,
            "qualified": qualified,
            "qualified_setups": qualified,
            "errors": errors,
            "rate_limited": rate_limited + watchlist_stats.get("rate_limited", 0),
            "heavy_rejections": heavy_rejection_count,
            "empty_data": empty_data_count,
            "no_signal": no_signal_count,
            "top_symbols": top_symbols[:10],
            "error_examples": combined_examples,
            "rejected_examples": watchlist_stats.get("rejected_examples", {}),
            "rejection_counts": {**watchlist_stats.get("rejection_counts", {}), **rejection_counts},
            "metric_snapshot": watchlist_stats.get("metric_snapshot", {}),
            "source": watchlist_stats.get("source", "dynamic_market_snapshot"),
        }
        return candidates

    async def _run_lane_scan(self, scan_type: str, scan_label: str, multiplier: int, timespan: str) -> Dict[str, Any]:
        watchlist = await self.universe_filter.build_daily_watchlist(scan_type=scan_type)
        candidates = await self._scan_symbols(watchlist["day_trade_equities"], multiplier, timespan, scan_label, scan_type)
        return {"stats": self.get_last_scan_stats(), "candidates": candidates}

    async def scan_day_trade_candidates(self) -> List[Dict[str, Any]]:
        return (await self._run_lane_scan("market", "day_trade", 5, "minute"))["candidates"]

    async def scan_market_overview(self) -> Dict[str, Any]:
        return await self._run_lane_scan("market", "market", 5, "minute")

    async def scan_premarket_overview(self) -> Dict[str, Any]:
        return await self._run_lane_scan("premarket", "premarket", 5, "minute")

    async def scan_midday_overview(self) -> Dict[str, Any]:
        return await self._run_lane_scan("midday", "midday", 5, "minute")

    async def scan_overnight_overview(self) -> Dict[str, Any]:
        return await self._run_lane_scan("overnight", "overnight", 1, "day")

    async def scan_swing_trade_candidates(self) -> List[Dict[str, Any]]:
        return (await self._run_lane_scan("overnight", "swing_trade", 1, "day"))["candidates"]

    async def scan_news_overview(self, limit: int = 8) -> Dict[str, Any]:
        if self.news_client is None:
            return {"headline_count": 0, "headlines": []}
        headlines = await self.news_client.fetch_market_news()
        return {"headline_count": len(headlines), "headlines": self.news_client.summarize_headlines(headlines, limit=limit)}

    async def scan_events_overview(self) -> Dict[str, Any]:
        if self.econ_client is None:
            return {"event_count": 0, "events": [], "high_impact_count": 0}
        events = await self.econ_client.fetch_events(date.today())
        return {"event_count": len(events), "high_impact_count": len(self.econ_client.high_impact_events(events)), "events": self.econ_client.summarize_events(events, limit=8)}

    async def scan_catalyst_overview(self, limit: int = 6) -> Dict[str, Any]:
        if self.news_client is None:
            return {"symbols_checked": 0, "catalysts": []}
        watchlist = await self.universe_filter.build_daily_watchlist(scan_type="market")
        symbols = watchlist["day_trade_equities"][:limit]
        rows = []
        for symbol in symbols:
            try:
                headlines = await self.news_client.fetch_ticker_news(symbol)
                top = self.news_client.summarize_headlines(headlines, limit=2)
                rows.append({"symbol": symbol, "headline_count": len(headlines), "headlines": top})
            except Exception as exc:
                rows.append({"symbol": symbol, "headline_count": 0, "headlines": [f"error: {self._compact_error(exc)}"]})
            await asyncio.sleep(0.25)
        return {"symbols_checked": len(symbols), "catalysts": rows}


    async def scan_ticker_overview(self, symbol: str, scan_type: str = "market") -> Dict[str, Any]:
        """Run a direct one-symbol scan without relying on the discovery passers list."""
        symbol = str(symbol or "").strip().upper()
        scan_type = str(scan_type or "market").strip().lower()
        aliases = {
            "day": "market",
            "day_trade": "market",
            "overall": "market",
            "scan": "market",
            "swing": "overnight",
            "swing_trade": "overnight",
            "news": "catalyst",
        }
        scan_type = aliases.get(scan_type, scan_type)
        if scan_type not in {"market", "premarket", "midday", "overnight", "catalyst"}:
            scan_type = "market"

        result: Dict[str, Any] = {
            "symbol": symbol,
            "scan_type": scan_type,
            "scan_timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "passed_filters": False,
            "strategy_signal": False,
            "qualified": False,
            "rejection_reason": None,
            "news_count": 0,
            "headlines": [],
        }
        if not symbol:
            result["error"] = "missing_symbol"
            return result

        today = date.today().isoformat()
        start = (date.today() - timedelta(days=3)).isoformat()

        if self.news_client is not None:
            try:
                headlines = await self.news_client.fetch_ticker_news(symbol, start_date=start, end_date=today)
                result["news_count"] = len(headlines)
                result["headlines"] = self.news_client.summarize_headlines(headlines, limit=5)
            except Exception as exc:
                result["headlines"] = [f"news_error: {self._compact_error(exc)}"]

        if scan_type == "catalyst":
            result["passed_filters"] = True
            result["qualified"] = bool(result.get("news_count", 0))
            if not result["qualified"]:
                result["rejection_reason"] = "no_recent_headlines"
            return result

        multiplier = 1 if scan_type == "overnight" else 5
        timespan = "day" if scan_type == "overnight" else "minute"

        try:
            heavy = await self.universe_filter.enrich_symbol_for_entry(symbol, scan_type=scan_type)
            result.update({
                "passes_heavy_filters": bool(heavy.get("passes_heavy_filters", True)),
                "heavy_rejection_reason": heavy.get("rejection_reason"),
                "premarket_volume": heavy.get("premarket_volume", 0),
                "premarket_gap_min_percent": heavy.get("premarket_gap_min_percent", 0),
                "max_float": heavy.get("max_float"),
            })
        except Exception as exc:
            result["passes_heavy_filters"] = False
            result["heavy_rejection_reason"] = f"heavy_filter_error: {self._compact_error(exc)}"

        try:
            df = await self.market_client.get_historical_data(symbol=symbol, multiplier=multiplier, timespan=timespan)
        except Exception as exc:
            result["error"] = f"market_data_error: {self._compact_error(exc)}"
            return result

        if df.empty:
            result["error"] = "empty_market_data"
            return result

        try:
            latest = df.dropna(subset=["close"]).iloc[-1]
            result["price"] = float(latest.get("close", 0) or 0)
            result["volume"] = float(latest.get("volume", 0) or 0)
            result["bars_loaded"] = int(len(df))
        except Exception:
            pass

        passes_lightweight = False
        metrics = {}
        try:
            filters = self.universe_filter._filters_for_scan(scan_type)
            metrics = self.universe_filter._compute_metrics(df, symbol)
            if metrics:
                passes_lightweight = self.universe_filter._passes_lightweight_filters(metrics, filters["descriptive"], filters["technical"])
                result.update({
                    "price": metrics.get("price", result.get("price")),
                    "volume": metrics.get("avg_daily_volume", result.get("volume")),
                    "relative_volume": metrics.get("relative_volume"),
                    "atr_pct": metrics.get("atr_pct"),
                    "gap_pct": metrics.get("gap_pct"),
                    "avg_dollar_volume": metrics.get("avg_dollar_volume"),
                })
        except Exception as exc:
            result["lightweight_filter_error"] = self._compact_error(exc)

        passes_heavy = bool(result.get("passes_heavy_filters", True))
        result["passed_filters"] = bool(passes_heavy and passes_lightweight)
        if not result["passed_filters"]:
            result["rejection_reason"] = result.get("heavy_rejection_reason") or "failed_lightweight_thresholds"

        try:
            payload = self.router.evaluate_ticker(symbol, df)
        except Exception as exc:
            result["strategy_error"] = self._compact_error(exc)
            payload = None

        if payload:
            result["strategy_signal"] = True
            result.update(payload)
        result["qualified"] = bool(result["passed_filters"] and result["strategy_signal"])
        if result["passed_filters"] and not result["strategy_signal"]:
            result["rejection_reason"] = "no_strategy_signal"
        return result

    async def scan_full_overview(self) -> Dict[str, Any]:
        return {
            "premarket": await self.scan_premarket_overview(),
            "market": await self.scan_market_overview(),
            "midday": await self.scan_midday_overview(),
            "overnight": await self.scan_overnight_overview(),
            "news": await self.scan_news_overview(),
            "events": await self.scan_events_overview(),
            "catalyst": await self.scan_catalyst_overview(),
        }
