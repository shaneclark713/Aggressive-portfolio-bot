from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List
import logging

from config.symbols import benchmark_for_symbol

logger = logging.getLogger("aggressive_portfolio_bot.data.scanners")


class ScannerService:
    def __init__(self, market_client, universe_filter, router):
        self.market_client = market_client
        self.universe_filter = universe_filter
        self.router = router
        self._last_scan_stats: Dict[str, Any] = {}

    def get_last_scan_stats(self) -> Dict[str, Any]:
        return dict(self._last_scan_stats)

    async def _scan_symbols(self, symbols: list[str], multiplier: int, timespan: str, scan_label: str) -> List[Dict[str, Any]]:
        candidates: List[Dict[str, Any]] = []
        errors = 0
        evaluated = 0
        top_symbols: List[str] = []
        scan_time = datetime.now(timezone.utc).isoformat()

        for symbol in symbols:
            try:
                df = await self.market_client.get_historical_data(
                    symbol=symbol,
                    multiplier=multiplier,
                    timespan=timespan,
                )
                if df.empty:
                    continue

                evaluated += 1
                payload = self.router.evaluate_ticker(symbol, df)
                if not payload:
                    continue

                payload["benchmark"] = benchmark_for_symbol(symbol)
                payload["scan_label"] = scan_label
                payload["scan_timestamp_utc"] = scan_time
                candidates.append(payload)
                top_symbols.append(symbol)
            except Exception as exc:
                errors += 1
                logger.exception("Scanner failed for %s during %s: %s", symbol, scan_label, exc)

        self._last_scan_stats = {
            "scan_label": scan_label,
            "scan_timestamp_utc": scan_time,
            "universe_loaded": len(symbols),
            "symbols_evaluated": evaluated,
            "qualified_setups": len(candidates),
            "errors": errors,
            "top_symbols": top_symbols[:10],
        }
        logger.info("Scan %s complete | universe=%s evaluated=%s setups=%s errors=%s", scan_label, len(symbols), evaluated, len(candidates), errors)
        return candidates

    async def scan_day_trade_candidates(self) -> List[Dict[str, Any]]:
        watchlist = await self.universe_filter.build_daily_watchlist()
        return await self._scan_symbols(
            watchlist["day_trade_equities"],
            multiplier=5,
            timespan="minute",
            scan_label="day_trade",
        )

    async def scan_swing_trade_candidates(self) -> List[Dict[str, Any]]:
        watchlist = await self.universe_filter.build_daily_watchlist()
        return await self._scan_symbols(
            watchlist["swing_trade_equities"],
            multiplier=1,
            timespan="day",
            scan_label="swing_trade",
        )
