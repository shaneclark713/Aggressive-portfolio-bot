from __future__ import annotations

from typing import Any

from execution.multi_leg import MultiLegOrderBuilder


class OptionsOrderService:
    def __init__(self):
        self.multi_leg_builder = MultiLegOrderBuilder()

    def _normalize_option_side(self, side: str) -> str:
        normalized = str(side or "buy_to_open").strip().upper()
        allowed = {"BUY_TO_OPEN", "SELL_TO_OPEN", "BUY_TO_CLOSE", "SELL_TO_CLOSE"}
        if normalized not in allowed:
            raise ValueError(f"Unsupported option side: {side}")
        return normalized

    def build_single_leg_order(
        self,
        option_symbol: str,
        side: str,
        quantity: int,
        order_type: str = "market",
        price: float | None = None,
        duration: str = "day",
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "order_type": str(order_type or "market").lower(),
            "option_symbol": option_symbol,
            "side": self._normalize_option_side(side),
            "quantity": int(quantity),
            "duration": str(duration or "day").lower(),
        }
        if price is not None:
            payload["price"] = float(price)
        return payload

    def build_vertical_spread_order(
        self,
        long_symbol: str,
        short_symbol: str,
        quantity: int,
        debit: bool = True,
        order_type: str = "market",
        price: float | None = None,
        duration: str = "day",
    ) -> dict[str, Any]:
        spread = self.multi_leg_builder.build_vertical_spread(long_symbol, short_symbol, quantity, debit=debit)
        valid, reason = self.multi_leg_builder.validate(spread)
        spread["is_valid"] = valid
        spread["validation_reason"] = reason
        spread["order_type"] = str(order_type or "market").lower()
        spread["duration"] = str(duration or "day").lower()
        if price is not None:
            spread["price"] = float(price)
        return spread
