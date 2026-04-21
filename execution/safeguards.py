from __future__ import annotations

from typing import Any, Dict


class ExecutionSafeguards:
    def __init__(self, config: dict | None = None):
        config = config or {}
        self.max_spread_pct = float(config.get("max_spread_pct", 0.03))
        self.min_volume = int(config.get("min_volume", 500_000))
        self.max_slippage_pct = float(config.get("max_slippage_pct", 0.02))
        self.halt_check_enabled = bool(config.get("halt_check_enabled", True))

    def validate_trade(self, data: Dict[str, Any]) -> tuple[bool, str]:
        price = float(data.get("price", 0) or 0)
        bid = float(data.get("bid", price) or price)
        ask = float(data.get("ask", price) or price)
        volume = int(data.get("volume", 0) or 0)
        halted = bool(data.get("halted", False))
        estimated_slippage_pct = float(data.get("estimated_slippage_pct", 0.0) or 0.0)

        if price <= 0:
            return False, "Invalid price"
        if self.halt_check_enabled and halted:
            return False, "Symbol appears halted"
        if volume < self.min_volume:
            return False, f"Volume too low ({volume})"

        spread_pct = abs(ask - bid) / price if price > 0 else 0.0
        if spread_pct > self.max_spread_pct:
            return False, f"Spread too wide ({spread_pct:.2%})"

        if estimated_slippage_pct > self.max_slippage_pct:
            return False, f"Slippage too high ({estimated_slippage_pct:.2%})"

        return True, "Execution safeguards passed"
