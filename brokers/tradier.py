from __future__ import annotations

import httpx


class TradierClient:
    def __init__(self, token, account_id, base_url="https://api.tradier.com/v1"):
        self.token = token
        self.account_id = account_id
        self.base_url = base_url.rstrip("/")
        self.timeout = 20.0

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
        }

    async def get_options_chain(self, symbol, expiration=None, greeks=True):
        params = {"symbol": symbol, "greeks": "true" if greeks else "false"}
        if expiration:
            params["expiration"] = expiration

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            res = await client.get(f"{self.base_url}/markets/options/chains", headers=self._headers(), params=params)
            res.raise_for_status()
            payload = res.json()

        chain = (((payload or {}).get("options") or {}).get("option")) or []
        if isinstance(chain, dict):
            chain = [chain]
        return chain

    async def place_option_order(self, symbol, qty, side, option_symbol):
        data = {
            "class": "option",
            "symbol": symbol,
            "option_symbol": option_symbol,
            "side": side,
            "quantity": qty,
            "type": "market",
            "duration": "day",
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            res = await client.post(f"{self.base_url}/accounts/{self.account_id}/orders", headers=self._headers(), data=data)
            res.raise_for_status()
            return res.json()

    async def place_multileg_order(self, symbol, legs, quantity=1, duration="day"):
        data = {
            "class": "multileg",
            "symbol": symbol,
            "duration": duration,
            "type": "market",
            "quantity": quantity,
        }
        for idx, leg in enumerate(list(legs), start=1):
            data[f"option_symbol[{idx}]"] = leg["option_symbol"]
            data[f"side[{idx}]"] = leg["action"].lower()
            data[f"quantity[{idx}]"] = int(leg["quantity"])

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            res = await client.post(f"{self.base_url}/accounts/{self.account_id}/orders", headers=self._headers(), data=data)
            res.raise_for_status()
            return res.json()
