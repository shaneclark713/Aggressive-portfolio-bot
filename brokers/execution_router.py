class ExecutionRouter:
    def __init__(self, ibkr_client, tradovate_client): self.ibkr=ibkr_client; self.tradovate=tradovate_client
    async def place_order(self, req):
        if req.broker=='IBKR': return await self.ibkr.place_order(req)
        if req.broker=='TRADOVATE': return await self.tradovate.place_order(req)
        raise ValueError(f'Unsupported broker: {req.broker}')
    async def close_bot_positions(self, broker, symbol=None, percent=None, quantity=None):
        if broker=='IBKR': return await self.ibkr.close_positions(symbol=symbol, percent=percent, quantity=quantity)
        raise ValueError('Tradovate close-position support should be issued as offsetting orders per trade state')
