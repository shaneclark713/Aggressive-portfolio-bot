class ExecutionRouter:
    def __init__(self, alpaca, tradier, config):
        self.alpaca = alpaca
        self.tradier = tradier
        self.config = config

    async def execute(self, trade):
        if trade["type"] == "stock":
            return await self._execute_stock(trade)

        elif trade["type"] == "option":
            return await self._execute_option(trade)

    async def _execute_stock(self, trade):
        if self.config["mode"] == "paper":
            print(f"[PAPER STOCK] {trade}")
            return

        return await self.alpaca.place_order(
            symbol=trade["symbol"],
            qty=trade["qty"],
            side=trade["side"]
        )

    async def _execute_option(self, trade):
        if self.config["mode"] == "paper":
            print(f"[PAPER OPTION] {trade}")
            return

        return await self.tradier.place_option_order(
            symbol=trade["symbol"],
            qty=trade["qty"],
            side=trade["side"],
            option_symbol=trade["option_symbol"]
        )
