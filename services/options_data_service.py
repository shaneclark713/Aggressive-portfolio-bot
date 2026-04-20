class OptionsDataService:
    def __init__(self, api_client):
        self.api = api_client

    async def get_chain(self, symbol):
        # Replace with your provider (Polygon/Alpaca/etc.)
        chain = await self.api.get_options_chain(symbol)

        return chain

    def normalize(self, raw_chain):
        contracts = []

        for c in raw_chain:
            contracts.append({
                "symbol": c["symbol"],
                "strike": c["strike"],
                "expiration": c["expiration"],
                "delta": c.get("delta", 0),
                "gamma": c.get("gamma", 0),
                "theta": c.get("theta", 0),
                "vega": c.get("vega", 0),
                "volume": c.get("volume", 0),
                "open_interest": c.get("open_interest", 0),
                "type": c.get("type")  # call/put
            })

        return contracts
