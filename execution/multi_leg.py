from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Iterable


@dataclass(slots=True)
class OptionLeg:
    option_symbol: str
    action: str
    quantity: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class MultiLegOrderBuilder:
    def build_vertical_spread(
        self,
        long_symbol: str,
        short_symbol: str,
        quantity: int,
        debit: bool = True,
    ) -> dict[str, Any]:
        opening_actions = ("BUY_TO_OPEN", "SELL_TO_OPEN") if debit else ("SELL_TO_OPEN", "BUY_TO_OPEN")
        legs = [
            OptionLeg(long_symbol, opening_actions[0], quantity).to_dict(),
            OptionLeg(short_symbol, opening_actions[1], quantity).to_dict(),
        ]
        return {
            "strategy_type": "vertical_spread",
            "quantity": quantity,
            "legs": legs,
        }

    def validate(self, order: dict[str, Any]) -> tuple[bool, str]:
        legs = list(order.get("legs", []))
        if len(legs) < 2:
            return False, "Multi-leg orders require at least two legs"
        for leg in legs:
            if not leg.get("option_symbol"):
                return False, "Missing option symbol in one or more legs"
            if int(leg.get("quantity", 0) or 0) <= 0:
                return False, "All legs require a positive quantity"
        return True, "Multi-leg order looks valid"

    def flatten_legs(self, order: dict[str, Any]) -> list[dict[str, Any]]:
        return [dict(leg) for leg in order.get("legs", [])]
