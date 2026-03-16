class TradeLogger:
    def __init__(self, trade_repo, sheets_ledger, settings): self.trade_repo=trade_repo; self.sheets_ledger=sheets_ledger; self.settings=settings
    def export_closed_trade(self, trade_id:str):
        row=self.trade_repo.get_trade(trade_id)
        if not row or row['status']!='CLOSED': return False
        data=dict(row); worksheet=self.settings.google_options_worksheet if data['broker']=='IBKR' else self.settings.google_futures_worksheet
        return self.sheets_ledger.append_trade(worksheet, data)
