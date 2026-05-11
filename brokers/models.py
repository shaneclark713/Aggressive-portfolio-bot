from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class OrderRequest:
    """Normalized order request passed from alerts into the execution router.

    This model intentionally stays broker-neutral. The execution router adapts it
    into Alpaca stock orders or Tradier option orders based on instrument_type and
    the currently selected execution mode.
    """

    trade_id: str
    broker: str
    symbol: str
    side: str
    instrument_type: str
    quantity: int | float
    order_type: str = "market"
    limit_price: float | None = None
    stop_price: float | None = None
    option_symbol: str | None = None
    option_right: str | None = None
    option_strike: float | None = None
    option_expiry: str | None = None
    time_in_force: str = "day"
    notes: str | None = None
    metadata: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        self.broker = (self.broker or "").upper()
        self.symbol = (self.symbol or "").upper()
        self.side = (self.side or "buy").lower()
        self.instrument_type = (self.instrument_type or "stock").lower()
        self.order_type = (self.order_type or "market").lower()
        self.time_in_force = (self.time_in_force or "day").lower()

        if not self.symbol:
            raise ValueError("OrderRequest requires a symbol")
        if self.quantity is None or float(self.quantity) <= 0:
            raise ValueError("OrderRequest quantity must be greater than zero")
