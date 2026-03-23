from __future__ import annotations

import aiohttp


class AlpacaClient:
    def __init__(self, api_key: str, secret_key: str, base_url: str):
        self.api_key = api_key or ""
        self.secret_key = secret_key or ""
        self.base_url = (base_url or "https://paper-api.alpaca.markets").rstrip("/")
        self.session: aiohttp.ClientSession | None = None

    async def connect(self) -> None:
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                headers={
                    "APCA-API-KEY-ID": self.api_key,
                    "APCA-API-SECRET-KEY": self.secret_key,
                    "Content-Type": "application/json",
                }
            )

    async def close(self) -> None:
        if self.session and not self.session.closed:
            await self.session.close()
        self.session = None

    def _ensure_ready(self) -> None:
        if not self.api_key or not self.secret_key:
            raise RuntimeError("Alpaca API credentials are missing")
        if self.session is None or self.session.closed:
            raise RuntimeError("Alpaca client is not connected")

    def _coerce_side(self, side: str) -> str:
        normalized = (side or "").strip().lower()
        if normalized in {"buy", "long"}:
            return "buy"
        if normalized in {"sell", "short"}:
            return "sell"
        raise ValueError(f"Unsupported Alpaca side: {side}")

    async def place_order(self, req):
        self._ensure_ready()

        qty = req.quantity
        if qty is None or float(qty) <= 0:
            raise ValueError("Order quantity must be greater than 0")

        payload = {
            "symbol": req.symbol,
            "qty": str(qty),
            "side": self._coerce_side(req.side),
            "type": (req.order_type or "market").lower(),
            "time_in_force": "day",
            "client_order_id": str(req.trade_id),
        }

        if payload["type"] == "limit":
            if req.limit_price is None:
                raise ValueError("Limit order requires limit_price")
            payload["limit_price"] = str(req.limit_price)

        if payload["type"] == "stop":
            if req.stop_price is None:
                raise ValueError("Stop order requires stop_price")
            payload["stop_price"] = str(req.stop_price)

        async with self.session.post(f"{self.base_url}/v2/orders", json=payload) as response:
            data = await response.json(content_type=None)
            if response.status >= 400:
                message = data.get("message") if isinstance(data, dict) else str(data)
                raise RuntimeError(f"Alpaca order failed ({response.status}): {message}")
            return data

    async def close_positions(self, symbol=None, percent=None, quantity=None):
        self._ensure_ready()

        if symbol:
            async with self.session.delete(f"{self.base_url}/v2/positions/{symbol}") as response:
                data = await response.json(content_type=None)
                if response.status >= 400:
                    message = data.get("message") if isinstance(data, dict) else str(data)
                    raise RuntimeError(f"Alpaca close failed ({response.status}): {message}")
                return data

        async with self.session.delete(f"{self.base_url}/v2/positions") as response:
            data = await response.json(content_type=None)
            if response.status >= 400:
                message = data.get("message") if isinstance(data, dict) else str(data)
                raise RuntimeError(f"Alpaca close-all failed ({response.status}): {message}")
            return data
