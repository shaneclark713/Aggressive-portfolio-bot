from datetime import datetime, timezone
import gspread
from google.oauth2.service_account import Credentials

class GoogleSheetsLedger:
    def __init__(self, credentials_dict:dict, spreadsheet_id:str, options_worksheet:str, futures_worksheet:str, monthly_summary_worksheet:str):
        self.credentials_dict=credentials_dict; self.spreadsheet_id=spreadsheet_id; self.options_worksheet=options_worksheet; self.futures_worksheet=futures_worksheet; self.monthly_summary_worksheet=monthly_summary_worksheet; self.client=None; self.workbook=None
    def connect(self):
        if not self.credentials_dict or not self.spreadsheet_id: return False
        creds=Credentials.from_service_account_info(self.credentials_dict, scopes=['https://www.googleapis.com/auth/spreadsheets','https://www.googleapis.com/auth/drive'])
        self.client=gspread.authorize(creds); self.workbook=self.client.open_by_key(self.spreadsheet_id); return True
    def append_trade(self, worksheet_name:str, trade_data:dict):
        if not self.workbook: return False
        sheet=self.workbook.worksheet(worksheet_name)
        row=[datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC'), trade_data.get('trade_id'), trade_data.get('broker_order_id'), trade_data.get('symbol'), trade_data.get('side'), trade_data.get('strategy'), trade_data.get('horizon'), trade_data.get('entry_time'), trade_data.get('exit_time'), trade_data.get('entry_price'), trade_data.get('exit_price'), trade_data.get('stop_loss'), trade_data.get('take_profit'), trade_data.get('pnl'), trade_data.get('rr_ratio'), trade_data.get('close_reason'), trade_data.get('entry_snapshot_path'), trade_data.get('close_snapshot_path'), trade_data.get('notes')]
        sheet.append_row(row, value_input_option='RAW'); return True
