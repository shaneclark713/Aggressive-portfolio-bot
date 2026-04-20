from __future__ import annotations


class TradeLogger:
    def __init__(self, trade_repo, sheets_ledger, settings):
        self.trade_repo = trade_repo
        self.sheets_ledger = sheets_ledger
        self.settings = settings

    def _worksheet_for_trade(self, data: dict) -> str:
        broker = str(data.get("broker", "")).upper()
        instrument_type = str(data.get("instrument_type", "")).lower()

        if broker == "TRADIER" or instrument_type == "option":
            return self.settings.google_options_worksheet

        return self.settings.google_futures_worksheet

    def export_closed_trade(self, trade_id: int | str):
        try:
            trade_id = int(trade_id)
        except Exception:
            return False

        row = self.trade_repo.get_trade_by_id(trade_id)
        if not row:
            return False

        if str(row.get("status", "")).upper() != "CLOSED":
            return False

        data = dict(row)
        worksheet = self._worksheet_for_trade(data)
        return self.sheets_ledger.append_trade(worksheet, data)
