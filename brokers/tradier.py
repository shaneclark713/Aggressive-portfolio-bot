from __future__ import annotations

import httpx


class TradierClient:
    def __init__(self, token, account_id, base_url="https://api.tradier.com/v1"):
        self.token = token or ""
        self.account_id = account_id or ""
        self.base_url = (base_url or "https://api.tradier.com/v1").rstrip("/")
        self.timeout = 20.0

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
        }

    def _ensure_market_ready(self) -> None:
        if not self.token:
            raise RuntimeError("Tradier API token is missing")

    def _ensure_trade_ready(self) -> None:
        self._ensure_market_ready()
        if not self.account_id:
            raise RuntimeError("Tradier account ID is missing")

    async def get_expirations(self, symbol: str) -> list[str]:
        self._ensure_market_ready()
        params = {
            "symbol": symbol,
            "includeAllRoots": "true",
            "strikes": "false",
            "contractSize": "false",
            "expirationType": "true",
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            res = await client.get(f"{self.base_url}/markets/options/expirations", headers=self._headers(), params=params)
            res.raise_for_status()
            payload = res.json()
        expirations = (((payload or {}).get("expirations") or {}).get("date")) or []
        if isinstance(expirations, str):
            return [expirations]
        if isinstance(expirations, list):
            return expirations
        return []

    async def get_options_chain(self, symbol, expiration=None, greeks=True):
        self._ensure_market_ready()
        if not expiration:
            expirations = await self.get_expirations(symbol)
            if not expirations:
                return []
            expiration = expirations[0]

        params = {"symbol": symbol, "expiration": expiration, "greeks": "true" if greeks else "false"}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            res = await client.get(f"{self.base_url}/markets/options/chains", headers=self._headers(), params=params)
            res.raise_for_status()
            payload = res.json()

        chain = (((payload or {}).get("options") or {}).get("option")) or []
        if isinstance(chain, dict):
            chain = [chain]
        return chain

    async def get_positions(self) -> list[dict]:
        self._ensure_trade_ready()
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            res = await client.get(f"{self.base_url}/accounts/{self.account_id}/positions", headers=self._headers())
            if res.status_code == 404:
                return []
            res.raise_for_status()
            payload = res.json()
        rows = (((payload or {}).get("positions") or {}).get("position")) or []
        if isinstance(rows, dict):
            return [rows]
        return rows if isinstance(rows, list) else []

    async def place_option_order(self, symbol, qty, side, option_symbol, order_type="market", price=None, stop=None, duration="day"):
        self._ensure_trade_ready()
        data = {
            "class": "option",
            "symbol": symbol,
            "option_symbol": option_symbol,
            "side": side,
            "quantity": int(qty),
            "type": order_type,
            "duration": duration,
        }
        if price is not None:
            data["price"] = price
        if stop is not None:
            data["stop"] = stop
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            res = await client.post(f"{self.base_url}/accounts/{self.account_id}/orders", headers=self._headers(), data=data)
            res.raise_for_status()
            return res.json()

    async def place_multileg_order(self, symbol, legs, quantity=1, duration="day", order_type="market", price=None):
        self._ensure_trade_ready()
        data = {
            "class": "multileg",
            "symbol": symbol,
            "duration": duration,
            "type": order_type,
            "quantity": int(quantity),
        }
        if price is not None:
            data["price"] = price
        for idx, leg in enumerate(list(legs), start=1):
            data[f"option_symbol[{idx}]"] = leg["option_symbol"]
            data[f"side[{idx}]"] = str(leg["action"]).lower()
            data[f"quantity[{idx}]"] = int(leg["quantity"])

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            res = await client.post(f"{self.base_url}/accounts/{self.account_id}/orders", headers=self._headers(), data=data)
            res.raise_for_status()
            return res.json()
