class WatchlistService:
    def __init__(self, universe_filter):
        self.universe_filter = universe_filter

    async def build_watchlists(self, scan_type: str = "market", force_refresh: bool = False):
        return await self.universe_filter.build_daily_watchlist(scan_type=scan_type, force_refresh=force_refresh)
