from __future__ import annotations

import json
from typing import Any, Iterable

from execution.live_position_state import LivePositionState


class TrailingStopService:
    SETTINGS_KEY = "runtime.trailing_positions"
    EXECUTION_SETTINGS_KEY = "__meta__.ui.execution_settings"

    def __init__(self, settings_repo):
        self.settings_repo = settings_repo

    def _load(self) -> dict[str, dict[str, Any]]:
        payload = self.settings_repo.get(self.SETTINGS_KEY, {}) or {}
        return payload if isinstance(payload, dict) else {}

    def _save(self, rows: dict[str, dict[str, Any]]) -> None:
        self.settings_repo.set(self.SETTINGS_KEY, rows)

    def _load_execution_settings(self) -> dict[str, Any]:
        overrides = self.settings_repo.get_filter_overrides()
        raw = overrides.get(self.EXECUTION_SETTINGS_KEY, {})
        if isinstance(raw, dict):
            return raw
        if isinstance(raw, str):
            try:
                parsed = json.loads(raw)
                return parsed if isinstance(parsed, dict) else {}
            except Exception:
                return {}
        return {}

    def get_default_trailing_config(self) -> dict[str, Any]:
        settings = self._load_execution_settings()
        trail_type = str(settings.get("trail_type") or "percent").lower()
        trail_value = settings.get("trail_value", 0.02)
        try:
            trail_value = float(trail_value)
        except Exception:
            trail_value = 0.02
        if trail_value <= 0:
            trail_value = 0.02
        return {"trail_type": trail_type, "trail_value": trail_value}

    def list_positions(self) -> dict[str, dict[str, Any]]:
        return self._load()

    def get_position(self, position_id: str) -> dict[str, Any] | None:
        return self._load().get(position_id)

    def create_position(
        self,
        position_id: str,
        entry_price: float,
        stop_loss: float,
        side: str = "LONG",
        symbol: str | None = None,
        quantity: float = 0,
        broker: str = "unknown",
        trail_type: str | None = None,
        trail_value: float | None = None,
        asset_type: str = "stock",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        defaults = self.get_default_trailing_config()
        resolved_trail_type = str(trail_type or defaults["trail_type"])
        resolved_trail_value = float(trail_value if trail_value is not None else defaults["trail_value"])
        state = LivePositionState(
            position_id=position_id,
            symbol=symbol or position_id,
            broker=broker,
            side=side,
            quantity=quantity,
            entry_price=entry_price,
            current_price=entry_price,
            initial_stop=stop_loss,
            active_stop=stop_loss,
            trail_type=resolved_trail_type,
            trail_value=resolved_trail_value,
            asset_type=asset_type,
            metadata=dict(metadata or {}),
        )
        rows = self._load()
        rows[position_id] = state.to_dict()
        self._save(rows)
        return rows[position_id]

    def sync_position(
        self,
        position_id: str,
        symbol: str,
        entry_price: float,
        current_price: float,
        stop_loss: float,
        side: str = "LONG",
        quantity: float = 0,
        broker: str = "unknown",
        trail_type: str | None = None,
        trail_value: float | None = None,
        asset_type: str = "stock",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        defaults = self.get_default_trailing_config()
        existing = self.get_position(position_id)
        if existing is None:
            created = self.create_position(
                position_id=position_id,
                symbol=symbol,
                entry_price=entry_price,
                stop_loss=stop_loss,
                side=side,
                quantity=quantity,
                broker=broker,
                trail_type=trail_type or defaults["trail_type"],
                trail_value=trail_value if trail_value is not None else defaults["trail_value"],
                asset_type=asset_type,
                metadata=metadata,
            )
            state = LivePositionState.from_dict(created)
        else:
            state = LivePositionState.from_dict(existing)
            state.symbol = symbol or state.symbol
            state.quantity = float(quantity or state.quantity or 0)
            state.entry_price = float(entry_price or state.entry_price or 0)
            state.initial_stop = float(stop_loss or state.initial_stop or 0)
            state.broker = broker or state.broker
            state.asset_type = asset_type or state.asset_type
            state.trail_type = str(trail_type or state.trail_type or defaults["trail_type"]).lower()
            state.trail_value = float(trail_value if trail_value is not None else state.trail_value or defaults["trail_value"])
            state.metadata = {**state.metadata, **dict(metadata or {})}
            state.metadata.pop("exit_reason", None)
        state.update_price(current_price)
        rows = self._load()
        rows[position_id] = state.to_dict()
        self._save(rows)
        return rows[position_id]

    def update_position(
        self,
        position_id: str,
        current_price: float,
        trail_type: str | None = None,
        trail_value: float | None = None,
    ) -> dict[str, Any] | None:
        existing = self.get_position(position_id)
        if existing is None:
            return None
        state = LivePositionState.from_dict(existing)
        if trail_type:
            state.trail_type = trail_type
        if trail_value is not None:
            state.trail_value = float(trail_value)
        state.update_price(current_price)
        rows = self._load()
        rows[position_id] = state.to_dict()
        self._save(rows)
        return rows[position_id]

    def remove_position(self, position_id: str) -> None:
        rows = self._load()
        rows.pop(position_id, None)
        self._save(rows)

    def prune_positions(self, keep_ids: Iterable[str], broker_prefixes: Iterable[str] | None = None) -> list[str]:
        keep = {str(item) for item in keep_ids}
        prefixes = tuple(broker_prefixes or ())
        rows = self._load()
        removed: list[str] = []
        for position_id in list(rows.keys()):
            if position_id in keep:
                continue
            if prefixes and not position_id.startswith(prefixes):
                continue
            removed.append(position_id)
            rows.pop(position_id, None)
        if removed:
            self._save(rows)
        return removed

    def list_triggered_positions(self, include_pending: bool = False) -> dict[str, dict[str, Any]]:
        rows = self._load()
        triggered: dict[str, dict[str, Any]] = {}
        for position_id, row in rows.items():
            if not row.get("stop_hit"):
                continue
            metadata = row.get("metadata") or {}
            if not include_pending and metadata.get("exit_submitted"):
                continue
            triggered[position_id] = row
        return triggered

    def _exit_side_for_state(self, state: dict[str, Any]) -> str:
        side = str(state.get("side") or "LONG").upper()
        asset_type = str(state.get("asset_type") or "stock").lower()
        if asset_type in {"option", "options"}:
            return "buy_to_close" if side in {"SHORT", "SELL", "SELL_SHORT"} else "sell_to_close"
        return "buy" if side in {"SHORT", "SELL", "SELL_SHORT"} else "sell"

    def build_exit_payloads(self, limit_buffer_pct: float = 0.0) -> list[dict[str, Any]]:
        payloads: list[dict[str, Any]] = []
        for position_id, state in self.list_triggered_positions().items():
            qty = float(state.get("quantity") or 0)
            if qty <= 0:
                continue
            asset_type = str(state.get("asset_type") or "stock").lower()
            order_type = "market"
            limit_price = None
            stop_price = float(state.get("active_stop") or 0)
            if limit_buffer_pct and stop_price > 0:
                buffer_value = abs(stop_price * float(limit_buffer_pct))
                side = str(state.get("side") or "LONG").upper()
                if asset_type in {"option", "options"}:
                    order_type = "limit"
                    limit_price = round(max(stop_price - buffer_value, 0.01), 4) if side not in {"SHORT", "SELL", "SELL_SHORT"} else round(stop_price + buffer_value, 4)
                elif side in {"SHORT", "SELL", "SELL_SHORT"}:
                    order_type = "limit"
                    limit_price = round(stop_price + buffer_value, 4)
                else:
                    order_type = "limit"
                    limit_price = round(max(stop_price - buffer_value, 0.01), 4)
            metadata = dict(state.get("metadata") or {})
            option_symbol = metadata.get("option_symbol") or metadata.get("raw", {}).get("option_symbol")
            payload = {
                "position_id": position_id,
                "symbol": state.get("symbol"),
                "type": "option" if asset_type in {"option", "options"} else "stock",
                "asset_type": asset_type,
                "side": self._exit_side_for_state(state),
                "qty": qty,
                "order_type": order_type,
                "limit_price": limit_price,
                "stop_price": stop_price if stop_price > 0 else None,
                "reason": "trailing_stop_trigger",
            }
            if option_symbol:
                payload["option_symbol"] = option_symbol
            payloads.append(payload)
        return payloads

    def mark_exit_pending(self, position_id: str, result: dict[str, Any] | None = None, reason: str = "trailing_stop_trigger") -> dict[str, Any] | None:
        rows = self._load()
        existing = rows.get(position_id)
        if existing is None:
            return None
        state = LivePositionState.from_dict(existing)
        state.metadata = dict(state.metadata or {})
        state.metadata["exit_submitted"] = True
        state.metadata["exit_reason"] = reason
        if result is not None:
            state.metadata["last_exit_result"] = result
        rows[position_id] = state.to_dict()
        self._save(rows)
        return rows[position_id]

    def mark_position_closed(self, position_id: str, reason: str = "closed") -> None:
        rows = self._load()
        existing = rows.get(position_id)
        if existing is None:
            return
        state = LivePositionState.from_dict(existing)
        state.metadata = dict(state.metadata or {})
        state.metadata["closed"] = True
        state.metadata["closed_reason"] = reason
        rows[position_id] = state.to_dict()
        self._save(rows)

    def evaluate_triggers(self) -> dict[str, dict[str, Any]]:
        return self.list_triggered_positions()
