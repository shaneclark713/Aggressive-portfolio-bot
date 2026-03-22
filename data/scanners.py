from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List
import logging

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

    async def _scan_symbols(self, symbols: list[str], multiplier: int, timespan: str, scan_label: str) -> List[Dict[str, Any]]:
        candidates: List[Dict[str, Any]] = []
        errors = 0
        evaluated = 0
        qualified = 0
        top_symbols: List[str] = []
        error_examples: list[str] = []
        scan_time = datetime.now(timezone.utc).isoformat()

        for symbol in symbols:
            try:
                df = await self.market_client.get_historical_data(symbol=symbol, multiplier=multiplier, timespan=timespan)
                if df.empty:
                    error_examples.append(f"{symbol}: empty_data")
                    continue
                evaluated += 1
                payload = self.router.evaluate_ticker(symbol, df)
                if not payload:
                    continue
                symbol_news_count = 0
                if self.news_client is not None:
                    try:
                        symbol_news = await self.news_client.fetch_ticker_news(symbol)
                        symbol_news_count = len(symbol_news)
                    except Exception:
                        pass
                payload["benchmark"] = benchmark_for_symbol(symbol)
                payload["scan_label"] = scan_label
                payload["scan_timestamp_utc"] = scan_time
                payload["news_count"] = symbol_news_count
                candidates.append(payload)
                qualified += 1
                top_symbols.append(symbol)
            except Exception as exc:
                errors += 1
                error_examples.append(f"{symbol}: {exc}")
                logger.exception("Scanner failed for %s during %s: %s", symbol, scan_label, exc)

        self._last_scan_stats = {
            "scan_label": scan_label,
            "scan_timestamp_utc": scan_time,
            "universe_loaded": len(symbols),
            "passed_universe_filters": len(symbols),
            "evaluated": evaluated,
            "symbols_evaluated": evaluated,
            "qualified": qualified,
            "qualified_setups": qualified,
            "errors": errors,
            "top_symbols": top_symbols[:10],
            "error_examples": error_examples[:10],
        }
        logger.info("Scan %s complete | universe=%s evaluated=%s setups=%s errors=%s", scan_label, len(symbols), evaluated, qualified, errors)
        return candidates

    async def scan_day_trade_candidates(self) -> List[Dict[str, Any]]:
        watchlist = await self.universe_filter.build_daily_watchlist()
        return await self._scan_symbols(watchlist["day_trade_equities"], multiplier=5, timespan="minute", scan_label="day_trade")

    async def scan_swing_trade_candidates(self) -> List[Dict[str, Any]]:
        watchlist = await self.universe_filter.build_daily_watchlist()
        return await self._scan_symbols(watchlist["swing_trade_equities"], multiplier=1, timespan="day", scan_label="swing_trade")
