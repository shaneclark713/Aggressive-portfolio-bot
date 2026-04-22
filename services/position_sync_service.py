from __future__ import annotations

from typing import Any


class PositionSyncService:
    def __init__(self, trailing_stop_service, alpaca_client=None, tradier_client=None):
        self.trailing_stop_service = trailing_stop_service
        self.alpaca_client = alpaca_client
        self.tradier_client = tradier_client

    def _default_stop(self, entry_price: float, side: str, pct: float = 0.02) -> float:
        price = float(entry_price or 0)
        if price <= 0:
            return 0.0
        if (side or "LONG").upper() in {"SHORT", "SELL", "SELL_SHORT"}:
            return round(price * (1 + pct), 8)
        return round(price * (1 - pct), 8)

    def _safe_float(self, value: Any, default: float = 0.0) -> float:
        try:
            return float(value)
        except Exception:
            return default

    def _alpaca_current_price(self, row: dict[str, Any], qty: float, entry_price: float) -> float:
        direct = self._safe_float(row.get("current_price") or row.get("current_price_last"), 0.0)
        if direct > 0:
            return direct
        market_value = abs(self._safe_float(row.get("market_value"), 0.0))
        if market_value > 0 and abs(qty) > 0:
            return market_value / abs(qty)
        lastday = self._safe_float(row.get("lastday_price"), 0.0)
        if lastday > 0:
            return lastday
        return entry_price

    def _normalize_alpaca_positions(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        normalized: list[dict[str, Any]] = []
        for row in rows or []:
            qty = self._safe_float(row.get("qty") or row.get("quantity"), 0.0)
            if qty == 0:
                continue
            side = str(row.get("side") or ("SHORT" if qty < 0 else "LONG")).upper()
            entry_price = self._safe_float(row.get("avg_entry_price"), 0.0)
            if entry_price <= 0:
                cost_basis = abs(self._safe_float(row.get("cost_basis"), 0.0))
                entry_price = (cost_basis / abs(qty)) if cost_basis > 0 and abs(qty) > 0 else 0.0
            symbol = str(row.get("symbol") or row.get("asset_symbol") or "UNKNOWN").upper()
            asset_class = str(row.get("asset_class") or row.get("asset_type") or "stock").lower()
            asset_type = "stock" if asset_class in {"us_equity", "equity", "stock"} else asset_class
            normalized.append(
                {
                    "position_id": f"alpaca:{symbol}",
                    "symbol": symbol,
                    "broker": "alpaca",
                    "side": side,
                    "quantity": abs(qty),
                    "entry_price": entry_price,
                    "current_price": self._alpaca_current_price(row, qty, entry_price),
                    "asset_type": asset_type,
                    "metadata": {"raw": row},
                }
            )
        return normalized

    def _tradier_asset_type(self, row: dict[str, Any]) -> str:
        explicit = str(row.get("asset_type") or row.get("type") or "").lower()
        if explicit:
            if "option" in explicit:
                return "option"
            if explicit in {"stock", "equity"}:
                return "stock"
        raw_option_symbol = row.get("option_symbol") or row.get("symbol")
        if raw_option_symbol and len(str(raw_option_symbol)) > 15 and any(ch.isdigit() for ch in str(raw_option_symbol)):
            return "option"
        return "stock"

    def _normalize_tradier_positions(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        normalized: list[dict[str, Any]] = []
        for row in rows or []:
            qty = self._safe_float(row.get("quantity"), 0.0)
            if qty == 0:
                continue
            asset_type = self._tradier_asset_type(row)
            symbol = str(row.get("symbol") or row.get("underlying") or "UNKNOWN").upper()
            option_symbol = row.get("option_symbol") or (symbol if asset_type == "option" else None)
            position_key = option_symbol if option_symbol else symbol
            entry_price = self._safe_float(row.get("cost_basis"), 0.0)
            if entry_price > 0 and abs(qty) > 0:
                entry_price = entry_price / abs(qty)
            current_price = self._safe_float(row.get("last") or row.get("mark"), 0.0)
            if current_price <= 0:
                close_value = abs(self._safe_float(row.get("close"), 0.0))
                if close_value > 0:
                    current_price = close_value
            if current_price <= 0:
                current_price = entry_price
            side = "SHORT" if qty < 0 else "LONG"
            normalized.append(
                {
                    "position_id": f"tradier:{position_key}",
                    "symbol": symbol,
                    "broker": "tradier",
                    "side": side,
                    "quantity": abs(qty),
                    "entry_price": entry_price,
                    "current_price": current_price,
                    "asset_type": asset_type,
                    "metadata": {"raw": row, "option_symbol": option_symbol},
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

    async def sync_live_positions(self, prune_missing: bool = True, include_demo_fallback: bool = False) -> dict[str, Any]:
        results: dict[str, Any] = {}
        live_ids: set[str] = set()
        live_position_count = 0

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
                    live_ids.add(row["position_id"])
                    live_position_count += 1
            except Exception as exc:
                results["alpaca_error"] = {"error": str(exc), "symbol": "ALPACA", "broker": "alpaca"}

        if self.tradier_client is not None and hasattr(self.tradier_client, "get_positions"):
            try:
                for row in self._normalize_tradier_positions(await self.tradier_client.get_positions()):
                    stop_pct = 0.05 if row["asset_type"] == "option" else 0.02
                    state = self.trailing_stop_service.sync_position(
                        position_id=row["position_id"],
                        symbol=row["symbol"],
                        entry_price=row["entry_price"],
                        current_price=row["current_price"],
                        stop_loss=self._default_stop(row["entry_price"], row["side"], pct=stop_pct),
                        side=row["side"],
                        quantity=row["quantity"],
                        broker=row["broker"],
                        asset_type=row["asset_type"],
                        metadata=row["metadata"],
                    )
                    results[row["position_id"]] = state
                    live_ids.add(row["position_id"])
                    live_position_count += 1
            except Exception as exc:
                results["tradier_error"] = {"error": str(exc), "symbol": "TRADIER", "broker": "tradier"}

        if prune_missing and live_ids:
            removed = self.trailing_stop_service.prune_positions(live_ids, broker_prefixes=("alpaca:", "tradier:"))
            if removed:
                results["pruned_positions"] = {"symbol": "PRUNED", "removed": removed, "count": len(removed)}

        if live_position_count == 0 and include_demo_fallback:
            results.update(await self.sync_demo_positions())

        return results

    async def sync_demo_positions(self) -> dict[str, Any]:
        return {
            "SPY-demo": await self.sync_stock_position("SPY-demo", "SPY", 510.0, 514.5, 505.0, "LONG"),
            "QQQ-demo": await self.sync_stock_position("QQQ-demo", "QQQ", 430.0, 426.0, 435.0, "SHORT"),
        }
