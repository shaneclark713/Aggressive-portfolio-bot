from enum import Enum
class ExecutionMode(str, Enum):
    ALERTS_ONLY='alerts_only'; APPROVAL_ONLY='approval_only'; AUTOMATED='automated'
class TradeHorizon(str, Enum):
    DAY_TRADE='DAY_TRADE'; SWING_TRADE='SWING_TRADE'
class TradeStatus(str, Enum):
    PENDING_ALERT='PENDING_ALERT'; EXPIRED='EXPIRED'; APPROVED='APPROVED'; REJECTED='REJECTED'; LIVE_SENT='LIVE_SENT'; OPEN='OPEN'; PARTIAL='PARTIAL'; CLOSED='CLOSED'; CANCELLED='CANCELLED'
class BrokerName(str, Enum):
    IBKR='IBKR'; TRADOVATE='TRADOVATE'
