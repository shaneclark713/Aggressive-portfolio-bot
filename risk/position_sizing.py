from __future__ import annotations

from math import floor


class PositionSizer:
    def __init__(self, max_risk_per_trade_pct: float):
        self.max_risk_per_trade_pct = (
            max_risk_per_trade_pct / 100.0
            if max_risk_per_trade_pct > 1
            else max_risk_per_trade_pct
        )

    def max_dollar_risk(self, account_equity: float) -> float:
        return account_equity * self.max_risk_per_trade_pct

    def size_shares(self, account_equity: float, entry: float, stop: float) -> int:
        per_share_risk = abs(entry - stop)
        if per_share_risk <= 0:
            return 0
        return max(0, floor(self.max_dollar_risk(account_equity) / per_share_risk))

    def size_option_contracts(self, account_equity: float, entry_premium: float, stop_premium: float) -> int:
        per_contract_risk = abs(entry_premium - stop_premium) * 100
        if per_contract_risk <= 0:
            return 0
        return max(0, floor(self.max_dollar_risk(account_equity) / per_contract_risk))

    def size_futures_contracts(self, account_equity: float, entry: float, stop: float, dollar_per_point: float) -> int:
        per_contract_risk = abs(entry - stop) * dollar_per_point
        if per_contract_risk <= 0:
            return 0
        return max(0, floor(self.max_dollar_risk(account_equity) / per_contract_risk))
