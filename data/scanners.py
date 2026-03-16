from config.symbols import benchmark_for_symbol

class ScannerService:
    def __init__(self, market_client, universe_filter, router): self.market_client=market_client; self.universe_filter=universe_filter; self.router=router
    async def scan_day_trade_candidates(self) -> list[dict]:
        watchlist=await self.universe_filter.build_daily_watchlist(); candidates=[]
        for symbol in watchlist['day_trade_equities']:
            df=await self.market_client.get_historical_data(symbol=symbol, multiplier=5, timespan='minute')
            payload=self.router.evaluate_ticker(symbol, df)
            if payload: payload['benchmark']=benchmark_for_symbol(symbol); candidates.append(payload)
        return candidates
