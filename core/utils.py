import uuid
from datetime import datetime
from zoneinfo import ZoneInfo

def new_trade_id() -> str:
    return uuid.uuid4().hex[:16]

def now_tz(timezone_name: str) -> datetime:
    return datetime.now(ZoneInfo(timezone_name))
