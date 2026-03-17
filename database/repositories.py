import json
from datetime import datetime
from typing import Any, Dict, List, Optional


class TradeRepository:
    def __init__(self, conn):
        self.conn = conn

    def create_trade(self, trade_data: Dict[str, Any]) -> int:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO active_trades (
                broker_order_id, symbol, side, strategy, horizon, status,
                entry_time, exit_time, entry_price, exit_price, stop_loss,
                take_profit, pnl, rr_ratio, close_reason,
                entry_snapshot_path, close_snapshot_path, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                trade_data.get("broker_order_id"),
                trade_data
