from __future__ import annotations


class WatchlistService:
    def __init__(self, universe_filter):
        self.universe_filter = universe_filter

    async def build_watchlists(self, scan_type: str | None = None):
        watchlists = await self.universe_filter.build_daily_watchlist()

        if scan_type is None:
            return watchlists

        if scan_type == "premarket":
            return {
                "day_trade_equities": watchlists.get("day_trade_equities", []),
                "swing_trade_equities": watchlists.get("swing_trade_equities", []),
                "futures": watchlists.get("futures", []),
            }

        if scan_type == "midday":
            return {
                "day_trade_equities": watchlists.get("day_trade_equities", []),
            }

        if scan_type == "overnight":
            return {
                "swing_trade_equities": watchlists.get("swing_trade_equities", []),
            }

        return watchlists
