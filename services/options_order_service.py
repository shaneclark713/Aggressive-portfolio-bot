from __future__ import annotations

from typing import Any

from execution.multi_leg import MultiLegOrderBuilder


class OptionsOrderService:
    def __init__(self):
        self.multi_leg_builder = MultiLegOrderBuilder()

    def build_single_leg_order(
        self,
        option_symbol: str,
        side: str,
        quantity: int,
    ) -> dict[str, Any]:
        return {
            "order_type": "single_leg_option",
            "option_symbol": option_symbol,
            "side": side.upper(),
            "quantity": int(quantity),
        }

    def build_vertical_spread_order(
        self,
        long_symbol: str,
        short_symbol: str,
        quantity: int,
        debit: bool = True,
    ) -> dict[str, Any]:
        spread = self.multi_leg_builder.build_vertical_spread(long_symbol, short_symbol, quantity, debit=debit)
        valid, reason = self.multi_leg_builder.validate(spread)
        spread["is_valid"] = valid
        spread["validation_reason"] = reason
        return spread
