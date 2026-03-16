class WatchlistService:
    def __init__(self, universe_filter):
        self.universe_filter = universe_filter

    async def build_watchlists(self):
        return await self.universe_filter.build_daily_watchlist()
