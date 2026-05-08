from datetime import datetime, timezone
import logging

import gspread

logger = logging.getLogger("aggressive_portfolio_bot.ledger.sheets_client")


class GoogleSheetsLedger:
    def __init__(self, credentials_dict: dict, spreadsheet_id: str, options_worksheet: str, futures_worksheet: str, monthly_summary_worksheet: str):
        self.credentials_dict = credentials_dict or {}
        self.spreadsheet_id = self._extract_spreadsheet_id(spreadsheet_id)
        self.options_worksheet = options_worksheet
        self.futures_worksheet = futures_worksheet
        self.monthly_summary_worksheet = monthly_summary_worksheet
        self.client = None
        self.workbook = None
        self.enabled = False
        self.last_error = None

    @staticmethod
    def _extract_spreadsheet_id(value):
        text = str(value or "").strip()
        marker = "/spreadsheets/d/"
        if marker in text:
            text = text.split(marker, 1)[1].split("/", 1)[0].split("?", 1)[0]
        return text

    def connect(self):
        self.enabled = False
        self.last_error = None
        if not self.credentials_dict or not self.spreadsheet_id:
            self.last_error = "Google Sheets disabled: missing credentials or spreadsheet id."
            logger.warning(self.last_error)
            return False
        try:
            self.client = gspread.service_account_from_dict(self.credentials_dict)
            self.workbook = self.client.open_by_key(self.spreadsheet_id)
            self.enabled = True
            logger.info("Google Sheets ledger connected: spreadsheet_id=%s", self.spreadsheet_id)
            return True
        except Exception as exc:
            self.client = None
            self.workbook = None
            self.last_error = f"Google Sheets disabled: {exc.__class__.__name__}: {exc}"
            logger.warning(self.last_error)
            return False

    def append_trade(self, worksheet_name: str, trade_data: dict):
        if not self.workbook:
            return False
        try:
            sheet = self.workbook.worksheet(worksheet_name)
            row = [
                datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
                trade_data.get("trade_id"),
                trade_data.get("broker_order_id"),
                trade_data.get("symbol"),
                trade_data.get("side"),
                trade_data.get("strategy"),
                trade_data.get("horizon"),
                trade_data.get("entry_time"),
                trade_data.get("exit_time"),
                trade_data.get("entry_price"),
                trade_data.get("exit_price"),
                trade_data.get("stop_loss"),
                trade_data.get("take_profit"),
                trade_data.get("pnl"),
                trade_data.get("rr_ratio"),
                trade_data.get("close_reason"),
                trade_data.get("entry_snapshot_path"),
                trade_data.get("close_snapshot_path"),
                trade_data.get("notes"),
            ]
            sheet.append_row(row, value_input_option="RAW")
            return True
        except Exception as exc:
            self.last_error = f"Google Sheets append failed: {exc.__class__.__name__}: {exc}"
            logger.warning(self.last_error)
            return False
