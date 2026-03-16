from dataclasses import dataclass
from typing import Any
@dataclass
class AppContext:
    settings: Any; scheduler: Any; db: Any; repositories: Any; config_service: Any; market_data: Any; news_data: Any; econ_calendar: Any; ibkr: Any; tradovate: Any; execution_router: Any; telegram_app: Any; sheets_ledger: Any
