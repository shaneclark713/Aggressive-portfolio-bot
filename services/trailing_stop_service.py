from __future__ import annotations

from typing import Any

from execution.live_position_state import LivePositionState


class TrailingStopService:
    SETTINGS_KEY = "runtime.trailing_positions"

    def __init__(self, settings_repo):
        self.settings_repo = settings_repo

    def _load(self) -> dict[str, dict[str, Any]]:
        payload = self.settings_repo.get(self.SETTINGS_KEY, {}) or {}
        return payload if isinstance(payload, dict) else {}

    def _save(self, rows: dict[str, dict[str, Any]]) -> None:
        self.settings_repo.set(self.SETTINGS_KEY, rows)

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
        trail_type: str = "percent",
        trail_value: float = 0.02,
        asset_type: str = "stock",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
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
            trail_type=trail_type,
            trail_value=trail_value,
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
        trail_type: str = "percent",
        trail_value: float = 0.02,
        asset_type: str = "stock",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
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
                trail_type=trail_type,
                trail_value=trail_value,
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
            state.metadata = {**state.metadata, **dict(metadata or {})}
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

    def evaluate_triggers(self) -> dict[str, dict[str, Any]]:
        return {position_id: row for position_id, row in self._load().items() if row.get("stop_hit")}
