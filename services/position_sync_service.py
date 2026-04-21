from __future__ import annotations

from typing import Any


class PositionSyncService:
    def __init__(self, trailing_stop_service, alpaca_client=None, tradier_client=None):
        self.trailing_stop_service = trailing_stop_service
        self.alpaca_client = alpaca_client
        self.tradier_client = tradier_client

    def _default_stop(self, entry_price: float, side: str, pct: float = 0.02) -> float:
        if (side or "LONG").upper() in {"SHORT", "SELL", "SELL_SHORT"}:
            return round(float(entry_price) * (1 + pct), 8)
        return round(float(entry_price) * (1 - pct), 8)

    def _normalize_alpaca_positions(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        normalized: list[dict[str, Any]] = []
        for row in rows or []:
            qty = float(row.get("qty") or row.get("quantity") or 0)
            side = str(row.get("side") or ("SHORT" if qty < 0 else "LONG")).upper()
            entry_price = float(row.get("avg_entry_price") or row.get("cost_basis") or 0)
            current_price = float(row.get("current_price") or row.get("market_value") or entry_price or 0)
            normalized.append(
                {
                    "position_id": f"alpaca:{row.get('symbol')}",
                    "symbol": str(row.get("symbol") or "UNKNOWN").upper(),
                    "broker": "alpaca",
                    "side": side,
                    "quantity": abs(qty),
                    "entry_price": entry_price,
                    "current_price": current_price if current_price > 0 else entry_price,
                    "asset_type": str(row.get("asset_class") or "stock"),
                    "metadata": {"raw": row},
                }
            )
        return normalized

    def _normalize_tradier_positions(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        normalized: list[dict[str, Any]] = []
        for row in rows or []:
            qty = float(row.get("quantity") or 0)
            entry_price = float(row.get("cost_basis") or 0)
            if qty and abs(qty) > 0 and entry_price > 0:
                entry_price = entry_price / abs(qty)
            side = "SHORT" if qty < 0 else "LONG"
            normalized.append(
                {
                    "position_id": f"tradier:{row.get('symbol')}",
                    "symbol": str(row.get("symbol") or "UNKNOWN").upper(),
                    "broker": "tradier",
                    "side": side,
                    "quantity": abs(qty),
                    "entry_price": entry_price,
                    "current_price": float(row.get("last") or row.get("mark") or entry_price or 0),
                    "asset_type": str(row.get("asset_type") or "position"),
                    "metadata": {"raw": row},
                }
            )
        return normalized

    async def sync_stock_position(
        self,
        position_id: str,
        symbol: str,
        entry_price: float,
        current_price: float,
        stop_loss: float,
        side: str = "LONG",
    ) -> dict[str, Any]:
        updated = self.trailing_stop_service.sync_position(
            position_id=position_id,
            symbol=symbol,
            entry_price=entry_price,
            current_price=current_price,
            stop_loss=stop_loss,
            side=side,
            broker="manual",
            asset_type="stock",
        )
        updated["position_id"] = position_id
        return updated

    async def sync_live_positions(self) -> dict[str, Any]:
        results: dict[str, Any] = {}

        if self.alpaca_client is not None and hasattr(self.alpaca_client, "get_positions"):
            try:
                for row in self._normalize_alpaca_positions(await self.alpaca_client.get_positions()):
                    state = self.trailing_stop_service.sync_position(
                        position_id=row["position_id"],
                        symbol=row["symbol"],
                        entry_price=row["entry_price"],
                        current_price=row["current_price"],
                        stop_loss=self._default_stop(row["entry_price"], row["side"]),
                        side=row["side"],
                        quantity=row["quantity"],
                        broker=row["broker"],
                        asset_type=row["asset_type"],
                        metadata=row["metadata"],
                    )
                    results[row["position_id"]] = state
            except Exception as exc:
                results["alpaca_error"] = {"error": str(exc)}

        if self.tradier_client is not None and hasattr(self.tradier_client, "get_positions"):
            try:
                for row in self._normalize_tradier_positions(await self.tradier_client.get_positions()):
                    state = self.trailing_stop_service.sync_position(
                        position_id=row["position_id"],
                        symbol=row["symbol"],
                        entry_price=row["entry_price"],
                        current_price=row["current_price"],
                        stop_loss=self._default_stop(row["entry_price"], row["side"], pct=0.05),
                        side=row["side"],
                        quantity=row["quantity"],
                        broker=row["broker"],
                        asset_type=row["asset_type"],
                        metadata=row["metadata"],
                    )
                    results[row["position_id"]] = state
            except Exception as exc:
                results["tradier_error"] = {"error": str(exc)}

        return results

    async def sync_demo_positions(self) -> dict[str, Any]:
        return {
            "SPY-demo": await self.sync_stock_position("SPY-demo", "SPY", 510.0, 514.5, 505.0, "LONG"),
            "QQQ-demo": await self.sync_stock_position("QQQ-demo", "QQQ", 430.0, 426.0, 435.0, "SHORT"),
        }
