from __future__ import annotations

from enum import Enum


class ExecutionMode(str, Enum):
    ALERTS_ONLY = "alerts_only"
    PAPER = "paper"
    LIVE = "live"


class TradeHorizon(str, Enum):
    DAY_TRADE = "DAY_TRADE"
    SWING_TRADE = "SWING_TRADE"


class TradeStatus(str, Enum):
    PENDING = "PENDING"
    EXPIRED = "EXPIRED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    PAPER = "PAPER"
    EXECUTED = "EXECUTED"
    EXECUTION_FAILED = "EXECUTION_FAILED"
    OPEN = "OPEN"
    PARTIAL = "PARTIAL"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"


class BrokerName(str, Enum):
    ALPACA = "ALPACA"
    TRADIER = "TRADIER"
