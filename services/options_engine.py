class OptionsEngine:
    def __init__(self, broker, data_service, config):
        self.broker = broker
        self.data = data_service
        self.config = config

    async def execute(self, signal):
        raw_chain = await self.data.get_chain(signal["symbol"])
        contracts = self.data.normalize(raw_chain)

        filtered = self.filter_contracts(contracts, signal)

        if not filtered:
            return

        best = self.select_best(filtered)

        return await self.broker.submit_order(
            symbol=best["symbol"],
            qty=1,
            side="buy",
            type="market",
            time_in_force="day"
        )

    def filter_contracts(self, contracts, signal):
        return [
            c for c in contracts
            if c["volume"] >= self.config.get("min_volume", 100)
            and c["open_interest"] >= self.config.get("min_oi", 100)
            and abs(c["delta"]) >= self.config.get("min_delta", 0.3)
            and c["type"] == self.config.get("option_type", "call")
        ]

    def select_best(self, contracts):
        # closest to ATM + highest volume
        contracts.sort(key=lambda x: (-x["volume"], abs(x["delta"] - 0.5)))
        return contracts[0]
