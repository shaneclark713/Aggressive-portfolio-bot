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
        if normalized in {"sell", "short", "sell_short"}:
            return "sell"
        raise ValueError(f"Unsupported Alpaca side: {side}")

    def _extract_request_fields(self, req=None, **kwargs) -> dict:
        if req is not None and not kwargs:
            return {
                "symbol": getattr(req, "symbol", None),
                "qty": getattr(req, "quantity", None),
                "side": getattr(req, "side", None),
                "order_type": getattr(req, "order_type", None),
                "limit_price": getattr(req, "limit_price", None),
                "stop_price": getattr(req, "stop_price", None),
                "time_in_force": getattr(req, "time_in_force", "day"),
                "client_order_id": getattr(req, "trade_id", None),
            }
        return {
            "symbol": kwargs.get("symbol"),
            "qty": kwargs.get("qty") or kwargs.get("quantity"),
            "side": kwargs.get("side"),
            "order_type": kwargs.get("order_type") or ("limit" if kwargs.get("limit_price") else "market"),
            "limit_price": kwargs.get("limit_price"),
            "stop_price": kwargs.get("stop_price"),
            "time_in_force": kwargs.get("time_in_force", "day"),
            "client_order_id": kwargs.get("client_order_id"),
        }

    async def place_order(self, req=None, **kwargs):
        self._ensure_ready()
        payload_input = self._extract_request_fields(req=req, **kwargs)

        qty = payload_input["qty"]
        if qty is None or float(qty) <= 0:
            raise ValueError("Order quantity must be greater than 0")

        payload = {
            "symbol": str(payload_input["symbol"] or "").upper(),
            "qty": str(qty),
            "side": self._coerce_side(str(payload_input["side"] or "buy")),
            "type": str(payload_input["order_type"] or "market").lower(),
            "time_in_force": str(payload_input["time_in_force"] or "day").lower(),
        }

        if payload_input["client_order_id"]:
            payload["client_order_id"] = str(payload_input["client_order_id"])

        if payload["type"] == "limit":
            if payload_input["limit_price"] is None:
                raise ValueError("Limit order requires limit_price")
            payload["limit_price"] = str(payload_input["limit_price"])

        if payload["type"] in {"stop", "stop_limit"}:
            if payload_input["stop_price"] is None:
                raise ValueError("Stop or stop_limit order requires stop_price")
            payload["stop_price"] = str(payload_input["stop_price"])

        if payload["type"] == "stop_limit":
            if payload_input["limit_price"] is None:
                raise ValueError("Stop limit order requires limit_price")
            payload["limit_price"] = str(payload_input["limit_price"])

        async with self.session.post(f"{self.base_url}/v2/orders", json=payload) as response:
            data = await response.json(content_type=None)
            if response.status >= 400:
                message = data.get("message") if isinstance(data, dict) else str(data)
                raise RuntimeError(f"Alpaca order failed ({response.status}): {message}")
            return data

    async def get_positions(self, symbol: str | None = None) -> list[dict]:
        self._ensure_ready()
        endpoint = f"{self.base_url}/v2/positions"
        if symbol:
            endpoint = f"{endpoint}/{symbol.upper()}"
        async with self.session.get(endpoint) as response:
            data = await response.json(content_type=None)
            if response.status == 404:
                return []
            if response.status >= 400:
                message = data.get("message") if isinstance(data, dict) else str(data)
                raise RuntimeError(f"Alpaca positions failed ({response.status}): {message}")
            if isinstance(data, list):
                return data
            if isinstance(data, dict):
                return [data]
            return []

    async def close_positions(self, symbol=None, percent=None, quantity=None):
        self._ensure_ready()

        if symbol:
            params = {}
            if percent is not None:
                params["percentage"] = str(percent)
            if quantity is not None:
                params["qty"] = str(quantity)
            async with self.session.delete(f"{self.base_url}/v2/positions/{symbol}", params=params) as response:
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
