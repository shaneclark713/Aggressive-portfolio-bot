import httpx

class TradierClient:
    def __init__(self, token, account_id, base_url="https://api.tradier.com/v1"):
        self.token = token
        self.account_id = account_id
        self.base_url = base_url

    async def get_options_chain(self, symbol):
        url = f"{self.base_url}/markets/options/chains"
        headers = {"Authorization": f"Bearer {self.token}"}
        params = {"symbol": symbol}

        async with httpx.AsyncClient() as client:
            res = await client.get(url, headers=headers, params=params)
            return res.json()

    async def place_option_order(self, symbol, qty, side, option_symbol):
        url = f"{self.base_url}/accounts/{self.account_id}/orders"

        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/x-www-form-urlencoded"
        }

        data = {
            "class": "option",
            "symbol": symbol,
            "option_symbol": option_symbol,
            "side": side,
            "quantity": qty,
            "type": "market",
            "duration": "day"
        }

        async with httpx.AsyncClient() as client:
            res = await client.post(url, headers=headers, data=data)
            return res.json()
