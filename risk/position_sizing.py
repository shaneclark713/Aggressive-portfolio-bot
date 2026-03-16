from math import floor
class PositionSizer:
    def __init__(self, max_risk_per_trade_pct: float): self.max_risk_per_trade_pct=max_risk_per_trade_pct/100.0 if max_risk_per_trade_pct>1 else max_risk_per_trade_pct
    def max_dollar_risk(self, account_equity: float) -> float: return account_equity*self.max_risk_per_trade_pct
    def size_shares(self, account_equity: float, entry: float, stop: float) -> int:
        r=abs(entry-stop); return max(0, floor(self.max_dollar_risk(account_equity)/r)) if r>0 else 0
    def size_option_contracts(self, account_equity: float, entry_premium: float, stop_premium: float) -> int:
        r=abs(entry_premium-stop_premium)*100; return max(0, floor(self.max_dollar_risk(account_equity)/r)) if r>0 else 0
    def size_futures_contracts(self, account_equity: float, entry: float, stop: float, dollar_per_point: float) -> int:
        r=abs(entry-stop)*dollar_per_point; return max(0, floor(self.max_dollar_risk(account_equity)/r)) if r>0 else 0
