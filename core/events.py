from dataclasses import dataclass
from typing import Optional
@dataclass
class AlertEvent:
    trade_id: str; symbol: str; strategy: str; side: str; execution_mode: str; message_id: Optional[int] = None
