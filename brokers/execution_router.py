from __future__ import annotations

from typing import Any, Dict


class ExecutionRouter:
    def __init__(self, alpaca_client=None, tradier_client=None, config_service=None):
        self.alpaca_client = alpaca_client
        self.tradier_client = tradier_client
        self.config_service = config_service

    def _mode(self) -> str:
        if self.config_service is None:
            return "paper"
        if hasattr(self.config_service, "get_execution_mode"):
            return self.config_service.get_execution_mode()
        if isinstance(self.config_service, dict):
            return self.config_service.get("mode", "paper")
        return "paper"

    async def execute(self, trade: Dict[str, Any]):
        trade_type = str(trade.get("type") or trade.get("instrument_type") or "stock").lower()
        if trade_type in {"option", "options"} and trade.get("legs"):
            return await self._execute_multileg_option(trade)
        if trade_type in {"option", "options"}:
            return await self._execute_option(trade)
        return await self._execute_stock(trade)

    async def _execute_stock(self, trade: Dict[str, Any]):
        mode = self._mode()
        if mode == "paper":
            return {"status": "paper", "trade": trade}

        if self.alpaca_client is None:
            raise RuntimeError("Alpaca client is not configured")

        symbol = trade["symbol"]
        qty = trade.get("qty", 1)
        side = trade.get("side", "buy")

        if hasattr(self.alpaca_client, "place_order"):
            return await self.alpaca_client.place_order(symbol=symbol, qty=qty, side=side)

        if hasattr(self.alpaca_client, "submit_order"):
            return await self.alpaca_client.submit_order(symbol=symbol, qty=qty, side=side, type="market", time_in_force="day")

        raise RuntimeError("Alpaca client does not expose a supported order method")

    async def _execute_option(self, trade: Dict[str, Any]):
        mode = self._mode()
        if mode == "paper":
            return {"status": "paper", "trade": trade}

        if self.tradier_client is None:
            raise RuntimeError("Tradier client is not configured")

        symbol = trade["symbol"]
        qty = trade.get("qty", 1)
        side = trade.get("side", "buy_to_open")
        option_symbol = trade.get("option_symbol")
        if not option_symbol:
            raise RuntimeError("Option trade missing option_symbol")

        return await self.tradier_client.place_option_order(symbol=symbol, qty=qty, side=side, option_symbol=option_symbol)

    async def _execute_multileg_option(self, trade: Dict[str, Any]):
        mode = self._mode()
        if mode == "paper":
            return {"status": "paper", "trade": trade}

        if self.tradier_client is None:
            raise RuntimeError("Tradier client is not configured")

        symbol = trade["symbol"]
        legs = list(trade.get("legs", []))
        quantity = int(trade.get("qty", trade.get("quantity", 1)) or 1)
        if not legs:
            raise RuntimeError("Multi-leg option trade missing legs")

        if not hasattr(self.tradier_client, "place_multileg_order"):
            raise RuntimeError("Tradier client does not expose a supported multi-leg order method")

        return await self.tradier_client.place_multileg_order(symbol=symbol, legs=legs, quantity=quantity)
