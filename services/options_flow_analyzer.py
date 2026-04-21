from __future__ import annotations

from typing import Any, Dict, Iterable


class OptionsFlowAnalyzer:
    def summarize(self, flow_rows: Iterable[dict]) -> Dict[str, Any]:
        bullish = 0
        bearish = 0
        premium = 0.0
        rows = list(flow_rows or [])

        for row in rows:
            side = str(row.get("side", "")).lower()
            notional = float(row.get("premium", 0.0) or 0.0)
            premium += notional
            if side in {"buy_call", "bullish", "call"}:
                bullish += 1
            elif side in {"buy_put", "bearish", "put"}:
                bearish += 1

        bias = "neutral"
        if bullish > bearish:
            bias = "bullish"
        elif bearish > bullish:
            bias = "bearish"

        return {
            "flow_count": len(rows),
            "bullish_flows": bullish,
            "bearish_flows": bearish,
            "total_premium": round(premium, 2),
            "bias": bias,
        }
