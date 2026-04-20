from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .enums import ExecutionMode


@dataclass(slots=True)
class AlertEvent:
    trade_id: str
    symbol: str
    strategy: str
    side: str
    execution_mode: ExecutionMode
    message_id: Optional[int] = None
