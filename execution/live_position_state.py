from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(slots=True)
class LivePositionState:
    position_id: str
    symbol: str
    broker: str
    side: str
    quantity: float
    entry_price: float
    current_price: float
    initial_stop: float
    active_stop: float
    trail_type: str = "percent"
    trail_value: float = 0.02
    best_price: float | None = None
    worst_price: float | None = None
    stop_hit: bool = False
    asset_type: str = "stock"
    metadata: dict[str, Any] = field(default_factory=dict)
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def __post_init__(self) -> None:
        self.side = (self.side or "LONG").upper()
        self.asset_type = (self.asset_type or "stock").lower()
        self.trail_type = (self.trail_type or "percent").lower()
        self.quantity = float(self.quantity or 0)
        self.entry_price = float(self.entry_price or 0)
        self.current_price = float(self.current_price or self.entry_price or 0)
        self.initial_stop = float(self.initial_stop or 0)
        self.active_stop = float(self.active_stop or self.initial_stop or 0)
        if self.best_price is None:
            self.best_price = self.current_price
        if self.worst_price is None:
            self.worst_price = self.current_price

    @property
    def is_short(self) -> bool:
        return self.side in {"SHORT", "SELL", "SELL_SHORT"}

    def _trail_stop_from_reference(self, reference_price: float) -> float:
        if self.trail_type == "absolute":
            offset = abs(float(self.trail_value or 0))
        else:
            offset = abs(reference_price * float(self.trail_value or 0))
        if self.is_short:
            return reference_price + offset
        return reference_price - offset

    def update_price(self, current_price: float) -> dict[str, Any]:
        price = float(current_price or 0)
        if price <= 0:
            return self.to_dict()

        self.current_price = price
        if self.best_price is None:
            self.best_price = price
        if self.worst_price is None:
            self.worst_price = price

        if self.is_short:
            self.best_price = min(float(self.best_price), price)
            self.worst_price = max(float(self.worst_price), price)
            candidate_stop = self._trail_stop_from_reference(float(self.best_price))
            if self.active_stop <= 0:
                self.active_stop = self.initial_stop or candidate_stop
            else:
                self.active_stop = min(self.active_stop, candidate_stop)
            if self.initial_stop > 0:
                self.active_stop = min(self.active_stop, self.initial_stop)
            self.stop_hit = price >= self.active_stop if self.active_stop > 0 else False
        else:
            self.best_price = max(float(self.best_price), price)
            self.worst_price = min(float(self.worst_price), price)
            candidate_stop = self._trail_stop_from_reference(float(self.best_price))
            if self.active_stop <= 0:
                self.active_stop = self.initial_stop or candidate_stop
            else:
                self.active_stop = max(self.active_stop, candidate_stop)
            if self.initial_stop > 0:
                self.active_stop = max(self.active_stop, self.initial_stop)
            self.stop_hit = price <= self.active_stop if self.active_stop > 0 else False

        self.updated_at = datetime.now(timezone.utc).isoformat()
        return self.to_dict()

    def to_dict(self) -> dict[str, Any]:
        return {
            "position_id": self.position_id,
            "symbol": self.symbol,
            "broker": self.broker,
            "side": self.side,
            "quantity": self.quantity,
            "entry_price": round(self.entry_price, 8),
            "current_price": round(self.current_price, 8),
            "initial_stop": round(self.initial_stop, 8),
            "active_stop": round(self.active_stop, 8),
            "trail_type": self.trail_type,
            "trail_value": float(self.trail_value or 0),
            "best_price": round(float(self.best_price or 0), 8),
            "worst_price": round(float(self.worst_price or 0), 8),
            "stop_hit": bool(self.stop_hit),
            "asset_type": self.asset_type,
            "metadata": dict(self.metadata or {}),
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "LivePositionState":
        return cls(
            position_id=str(payload.get("position_id") or payload.get("id") or payload.get("symbol") or "position"),
            symbol=str(payload.get("symbol") or "UNKNOWN"),
            broker=str(payload.get("broker") or "unknown"),
            side=str(payload.get("side") or "LONG"),
            quantity=float(payload.get("quantity", 0) or 0),
            entry_price=float(payload.get("entry_price", 0) or 0),
            current_price=float(payload.get("current_price", payload.get("entry_price", 0)) or 0),
            initial_stop=float(payload.get("initial_stop", payload.get("active_stop", 0)) or 0),
            active_stop=float(payload.get("active_stop", payload.get("initial_stop", 0)) or 0),
            trail_type=str(payload.get("trail_type") or "percent"),
            trail_value=float(payload.get("trail_value", 0.02) or 0.02),
            best_price=float(payload.get("best_price", payload.get("current_price", 0)) or 0),
            worst_price=float(payload.get("worst_price", payload.get("current_price", 0)) or 0),
            stop_hit=bool(payload.get("stop_hit", False)),
            asset_type=str(payload.get("asset_type") or "stock"),
            metadata=dict(payload.get("metadata") or {}),
            updated_at=str(payload.get("updated_at") or datetime.now(timezone.utc).isoformat()),
        )
