from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

from config.symbols import benchmark_for_symbol


class ScannerService:
    def __init__(self, market_client, universe_filter, router):
        self.market_client = market_client
        self.universe_filter = universe_filter
        self.router = router

    async def _scan_symbols(self, symbols: list[str], multiplier: int, timespan: str, scan_label: str) -> List[Dict[str, Any]]:
        candidates: List[Dict[str, Any]] = []
        for symbol in symbols:
            df = await self.market_client.get_historical_data(
                symbol=symbol,
                multiplier=multiplier,
                timespan=timespan,
            )
            if df.empty:
                continue

            payload = self.router.evaluate_ticker(symbol, df)
            if not payload:
                continue

            payload["benchmark"] = benchmark_for_symbol(symbol)
            payload["scan_label"] = scan_label
            payload["scan_timestamp_utc"] = datetime.now(timezone.utc).isoformat()
            candidates.append(payload)
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
