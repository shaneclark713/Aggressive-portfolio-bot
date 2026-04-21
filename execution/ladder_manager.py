from __future__ import annotations

from typing import Any


class LadderManager:
    def build_entry_ladder(
        self,
        entry_price: float,
        side: str,
        total_size: int,
        steps: int = 3,
        spacing_pct: float = 0.01,
    ) -> list[dict[str, Any]]:
        if total_size <= 0 or steps <= 0:
            return []

        base_qty = total_size // steps
        remainder = total_size % steps
        ladder = []
        side = side.upper()

        for idx in range(steps):
            qty = base_qty + (1 if idx < remainder else 0)
            if qty <= 0:
                continue

            offset = spacing_pct * idx
            if side in {"LONG", "BUY"}:
                price = entry_price * (1 - offset)
                action = "BUY"
            else:
                price = entry_price * (1 + offset)
                action = "SELL_SHORT"

            ladder.append(
                {
                    "step": idx + 1,
                    "action": action,
                    "qty": qty,
                    "limit_price": round(price, 4),
                }
            )
        return ladder

    def build_exit_ladder(
        self,
        entry_price: float,
        side: str,
        total_size: int,
        rr_targets: list[float],
        risk_per_unit: float,
    ) -> list[dict[str, Any]]:
        if total_size <= 0 or risk_per_unit <= 0 or not rr_targets:
            return []

        steps = len(rr_targets)
        base_qty = total_size // steps
        remainder = total_size % steps
        exits = []
        side = side.upper()

        for idx, rr in enumerate(rr_targets):
            qty = base_qty + (1 if idx < remainder else 0)
            if qty <= 0:
                continue

            target_move = risk_per_unit * float(rr)
            if side in {"LONG", "BUY"}:
                price = entry_price + target_move
                action = "SELL"
            else:
                price = entry_price - target_move
                action = "BUY_TO_COVER"

            exits.append(
                {
                    "step": idx + 1,
                    "action": action,
                    "qty": qty,
                    "rr_target": rr,
                    "limit_price": round(price, 4),
                }
            )
        return exits
