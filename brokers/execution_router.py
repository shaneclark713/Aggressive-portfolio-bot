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
            mode = self.config_service.get_execution_mode()
        elif isinstance(self.config_service, dict):
            mode = self.config_service.get("mode", "paper")
        else:
            mode = "paper"
        normalized = str(mode or "paper").lower()
        return {"approval_only": "paper", "automated": "live", "alerts_only": "alerts_only"}.get(normalized, normalized)

    async def execute(self, trade: Dict[str, Any]):
        trade_type = str(trade.get("type") or trade.get("instrument_type") or "stock").lower()
        if self._mode() == "alerts_only":
            return {"status": "alerts_only", "trade": trade}
        if trade_type in {"option", "options"} and trade.get("legs"):
            return await self._execute_multileg_option(trade)
        if trade_type in {"option", "options"}:
            return await self._execute_option(trade)
        return await self._execute_stock(trade)

    async def _execute_stock(self, trade: Dict[str, Any]):
        if self._mode() == "paper":
            return {"status": "paper", "trade": trade}
        if self.alpaca_client is None:
            raise RuntimeError("Alpaca client is not configured")

        payload = {
            "symbol": str(trade["symbol"]).upper(),
            "qty": trade.get("qty", 1),
            "side": trade.get("side", "buy"),
            "limit_price": trade.get("limit_price"),
            "stop_price": trade.get("stop_price"),
            "order_type": trade.get("order_type") or ("limit" if trade.get("limit_price") else "market"),
            "time_in_force": trade.get("time_in_force", "day"),
            "client_order_id": trade.get("client_order_id") or f"{trade.get('symbol','UNK')}-{trade.get('step','0')}",
        }
        return await self.alpaca_client.place_order(**payload)

    async def _execute_option(self, trade: Dict[str, Any]):
        if self._mode() == "paper":
            return {"status": "paper", "trade": trade}
        if self.tradier_client is None:
            raise RuntimeError("Tradier client is not configured")

        symbol = trade["symbol"]
        qty = trade.get("qty", trade.get("quantity", 1))
        side = str(trade.get("side", "buy_to_open")).lower()
        option_symbol = trade.get("option_symbol")
        if not option_symbol:
            raise RuntimeError("Option trade missing option_symbol")

        return await self.tradier_client.place_option_order(
            symbol=symbol,
            qty=qty,
            side=side,
            option_symbol=option_symbol,
            order_type=str(trade.get("order_type") or "market").lower(),
            price=trade.get("price"),
            stop=trade.get("stop"),
            duration=str(trade.get("duration") or "day").lower(),
        )

    async def _execute_multileg_option(self, trade: Dict[str, Any]):
        if self._mode() == "paper":
            return {"status": "paper", "trade": trade}
        if self.tradier_client is None:
            raise RuntimeError("Tradier client is not configured")

        symbol = trade["symbol"]
        legs = list(trade.get("legs", []))
        quantity = int(trade.get("qty", trade.get("quantity", 1)) or 1)
        if not legs:
            raise RuntimeError("Multi-leg option trade missing legs")

        return await self.tradier_client.place_multileg_order(
            symbol=symbol,
            legs=legs,
            quantity=quantity,
            duration=str(trade.get("duration") or "day").lower(),
            order_type=str(trade.get("order_type") or "market").lower(),
            price=trade.get("price"),
        )
