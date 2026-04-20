from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class AppContext:
    settings: Any
    scheduler: Any
    db: Any
    repositories: Any
    config_service: Any
    market_data: Any
    news_data: Any
    econ_calendar: Any
    alpaca: Any
    tradier: Any
    execution_router: Any
    telegram_app: Any
    sheets_ledger: Any
