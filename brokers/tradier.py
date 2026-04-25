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

    def _parse_expiration_payload(self, payload: dict) -> list[str]:
        """Normalize Tradier expiration responses into a list of date strings.

        Tradier returns different response shapes depending on expirationType.
        With expirationType=true, the payload may contain an ``expiration`` list
        of objects instead of a plain ``date`` list. The old parser only handled
        the plain ``date`` shape, so refresh could stop after /expirations and
        never request /chains.
        """
        expirations_block = (payload or {}).get("expirations") or {}
        raw = expirations_block.get("date")
        if raw is None:
            raw = expirations_block.get("expiration")

        if isinstance(raw, str):
            return [raw]

        dates: list[str] = []
        if isinstance(raw, list):
            for item in raw:
                if isinstance(item, str):
                    dates.append(item)
                elif isinstance(item, dict):
                    date_value = item.get("date") or item.get("expiration")
                    if date_value:
                        dates.append(str(date_value))

        seen: set[str] = set()
        normalized: list[str] = []
        for value in dates:
            date_text = str(value).strip()
            if date_text and date_text not in seen:
                seen.add(date_text)
                normalized.append(date_text)
        return normalized

    async def get_expirations(self, symbol: str) -> list[str]:
        self._ensure_market_ready()
        symbol = str(symbol or "").upper().strip()
        base_params = {
            "symbol": symbol,
            "includeAllRoots": "true",
            "strikes": "false",
            "contractSize": "false",
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for expiration_type in ("true", "false"):
                params = {**base_params, "expirationType": expiration_type}
                res = await client.get(
                    f"{self.base_url}/markets/options/expirations",
                    headers=self._headers(),
                    params=params,
                )
                res.raise_for_status()
                dates = self._parse_expiration_payload(res.json())
                if dates:
                    return dates
        return []

    async def get_options_chain(self, symbol, expiration=None, greeks=True):
        self._ensure_market_ready()
        symbol = str(symbol or "").upper().strip()
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
        return chain if isinstance(chain, list) else []

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
