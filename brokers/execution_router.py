class ExecutionRouter:
    def __init__(self, ibkr_client=None, tradovate_client=None, alpaca_client=None):
        self.ibkr = ibkr_client
        self.tradovate = tradovate_client
        self.alpaca = alpaca_client

    async def place_order(self, req):
        broker = (req.broker or "").upper()
        if broker == "IBKR":
            return await self.ibkr.place_order(req)
        if broker == "TRADOVATE":
            return await self.tradovate.place_order(req)
        if broker == "ALPACA":
            return await self.alpaca.place_order(req)
        raise ValueError(f"Unsupported broker: {req.broker}")

    async def close_bot_positions(self, broker, symbol=None, percent=None, quantity=None):
        broker = (broker or "").upper()
        if broker == "IBKR":
            return await self.ibkr.close_positions(symbol=symbol, percent=percent, quantity=quantity)
        if broker == "ALPACA":
            return await self.alpaca.close_positions(symbol=symbol, percent=percent, quantity=quantity)
        raise ValueError("Tradovate close-position support should be issued as offsetting orders per trade state")
