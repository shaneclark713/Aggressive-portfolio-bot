from __future__ import annotations

from typing import Any


class TrailingManager:
    def initial_state(
        self,
        entry_price: float,
        stop_loss: float,
        side: str,
        trail_type: str = "percent",
        trail_value: float = 0.02,
    ) -> dict[str, Any]:
        return {
            "entry_price": float(entry_price),
            "active_stop": float(stop_loss),
            "side": side.upper(),
            "trail_type": trail_type,
            "trail_value": float(trail_value),
            "best_price": float(entry_price),
        }

    def update(self, state: dict[str, Any], current_price: float) -> dict[str, Any]:
        current_price = float(current_price)
        side = str(state.get("side", "LONG")).upper()
        best_price = float(state.get("best_price", current_price))
        active_stop = float(state.get("active_stop", current_price))
        trail_type = str(state.get("trail_type", "percent"))
        trail_value = float(state.get("trail_value", 0.02))

        if side in {"LONG", "BUY"}:
            best_price = max(best_price, current_price)
            if trail_type == "percent":
                new_stop = best_price * (1 - trail_value)
            else:
                new_stop = best_price - trail_value
            active_stop = max(active_stop, new_stop)
        else:
            best_price = min(best_price, current_price)
            if trail_type == "percent":
                new_stop = best_price * (1 + trail_value)
            else:
                new_stop = best_price + trail_value
            active_stop = min(active_stop, new_stop)

        updated = dict(state)
        updated["best_price"] = round(best_price, 4)
        updated["active_stop"] = round(active_stop, 4)
        updated["current_price"] = round(current_price, 4)
        updated["stop_hit"] = current_price <= active_stop if side in {"LONG", "BUY"} else current_price >= active_stop
        return updated
