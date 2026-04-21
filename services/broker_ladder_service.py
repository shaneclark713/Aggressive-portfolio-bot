from __future__ import annotations

from typing import Any


class BrokerLadderService:
    def __init__(self, execution_router):
        self.execution_router = execution_router

    async def submit_stock_ladder(self, symbol: str, side: str, entries: list[dict[str, Any]]) -> dict[str, Any]:
        results: list[dict[str, Any]] = []
        normalized_side = "buy" if side.upper() in {"LONG", "BUY"} else "sell"
        for row in entries:
            qty = int(row.get("qty", 0) or 0)
            if qty <= 0:
                continue
            payload = {
                "type": "stock",
                "symbol": symbol,
                "side": normalized_side,
                "qty": qty,
                "limit_price": float(row.get("limit_price", 0) or 0),
                "order_subtype": "ladder_leg",
                "step": int(row.get("step", 0) or 0),
            }
            result = await self.execution_router.execute(payload)
            results.append({"leg": payload, "result": result})
        return {"symbol": symbol, "submitted_legs": len(results), "results": results}

    async def submit_exit_ladder(self, symbol: str, exits: list[dict[str, Any]]) -> dict[str, Any]:
        results: list[dict[str, Any]] = []
        for row in exits:
            qty = int(row.get("qty", 0) or 0)
            if qty <= 0:
                continue
            action = str(row.get("action") or "SELL").upper()
            payload = {
                "type": "stock",
                "symbol": symbol,
                "side": "buy" if action == "BUY_TO_COVER" else "sell",
                "qty": qty,
                "limit_price": float(row.get("limit_price", 0) or 0),
                "order_subtype": "exit_ladder_leg",
                "step": int(row.get("step", 0) or 0),
                "rr_target": row.get("rr_target"),
            }
            result = await self.execution_router.execute(payload)
            results.append({"leg": payload, "result": result})
        return {"symbol": symbol, "submitted_legs": len(results), "results": results}
