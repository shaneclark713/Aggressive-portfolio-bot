import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional


class TradeRepository:
    def __init__(self, conn):
        self.conn = conn

    def create_trade(self, trade_data: Dict[str, Any]) -> int:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO active_trades (
                broker_order_id,
                symbol,
                side,
                strategy,
                horizon,
                status,
                entry_time,
                exit_time,
                entry_price,
                exit_price,
                stop_loss,
                take_profit,
                pnl,
                rr_ratio,
                close_reason,
                entry_snapshot_path,
                close_snapshot_path,
                notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                trade_data.get("broker_order_id"),
                trade_data.get("symbol"),
                trade_data.get("side"),
                trade_data.get("strategy"),
                trade_data.get("horizon"),
                trade_data.get("status", "OPEN"),
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
            ),
        )
        self.conn.commit()
        return cursor.lastrowid

    def get_open_trades(self) -> List[Dict[str, Any]]:
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM active_trades WHERE status = 'OPEN' ORDER BY trade_id DESC"
        )
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    def get_recent_closed_trades(self, limit: int = 25) -> List[Dict[str, Any]]:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT * FROM active_trades
            WHERE status = 'CLOSED'
            ORDER BY COALESCE(exit_time, entry_time) DESC, trade_id DESC
            LIMIT ?
            """,
            (int(limit),),
        )
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    def get_consecutive_loss_count(self, limit: int = 50) -> int:
        count = 0
        for trade in self.get_recent_closed_trades(limit=limit):
            try:
                pnl = float(trade.get("pnl", 0) or 0)
            except Exception:
                pnl = 0.0
            if pnl < 0:
                count += 1
                continue
            break
        return count

    def get_trade_by_id(self, trade_id: int) -> Optional[Dict[str, Any]]:
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM active_trades WHERE trade_id = ?",
            (trade_id,),
        )
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_open_trade_by_symbol(self, symbol: str) -> Optional[Dict[str, Any]]:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT * FROM active_trades
            WHERE symbol = ? AND status = 'OPEN'
            ORDER BY trade_id DESC
            LIMIT 1
            """,
            (symbol,),
        )
        row = cursor.fetchone()
        return dict(row) if row else None

    def close_trade(
        self,
        trade_id: int,
        exit_price: float,
        pnl: float,
        close_reason: str,
        exit_time: Optional[str] = None,
        close_snapshot_path: Optional[str] = None,
    ) -> None:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            UPDATE active_trades
            SET status = 'CLOSED',
                exit_price = ?,
                pnl = ?,
                close_reason = ?,
                exit_time = ?,
                close_snapshot_path = ?
            WHERE trade_id = ?
            """,
            (
                exit_price,
                pnl,
                close_reason,
                exit_time or datetime.utcnow().isoformat(),
                close_snapshot_path,
                trade_id,
            ),
        )
        self.conn.commit()

    def update_trade_status(self, trade_id: int, status: str) -> None:
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE active_trades SET status = ? WHERE trade_id = ?",
            (status, trade_id),
        )
        self.conn.commit()


class AlertRepository:
    def __init__(self, conn):
        self.conn = conn
        self._ensure_table()

    def _ensure_table(self) -> None:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS alerts (
                alert_id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                strategy TEXT,
                side TEXT,
                payload TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'PENDING',
                created_at TEXT NOT NULL,
                responded_at TEXT
            )
            """
        )
        self.conn.commit()

    def create_alert(self, payload: Dict[str, Any]) -> int:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO alerts (symbol, strategy, side, payload, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                payload.get("symbol"),
                payload.get("strategy"),
                payload.get("side"),
                json.dumps(payload),
                payload.get("status", "PENDING"),
                datetime.utcnow().isoformat(),
            ),
        )
        self.conn.commit()
        return cursor.lastrowid

    def update_alert_status(self, alert_id: int, status: str) -> None:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            UPDATE alerts
            SET status = ?, responded_at = ?
            WHERE alert_id = ?
            """,
            (status, datetime.utcnow().isoformat(), alert_id),
        )
        self.conn.commit()

    def get_pending_alerts(self) -> List[Dict[str, Any]]:
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM alerts WHERE status = 'PENDING' ORDER BY alert_id DESC"
        )
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    def get_expired_alerts(self, timeout_seconds: int = 180) -> List[Dict[str, Any]]:
        cutoff = (datetime.utcnow() - timedelta(seconds=timeout_seconds)).isoformat()
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT * FROM alerts
            WHERE status = 'PENDING' AND created_at <= ?
            ORDER BY alert_id ASC
            """,
            (cutoff,),
        )
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    def mark_alert_expired(self, alert_id: int) -> None:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            UPDATE alerts
            SET status = 'EXPIRED', responded_at = ?
            WHERE alert_id = ?
            """,
            (datetime.utcnow().isoformat(), alert_id),
        )
        self.conn.commit()


class ExecutionLogRepository:
    def __init__(self, conn):
        self.conn = conn

    def log_event(
        self,
        event_type: str,
        payload: Dict[str, Any],
        trade_id: Optional[int] = None,
        event_time: Optional[str] = None,
    ) -> int:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO trade_audit_log (trade_id, event_type, event_time, payload)
            VALUES (?, ?, ?, ?)
            """,
            (
                trade_id,
                event_type,
                event_time or datetime.utcnow().isoformat(),
                json.dumps(payload),
            ),
        )
        self.conn.commit()
        return cursor.lastrowid

    def get_events_for_trade(self, trade_id: int) -> List[Dict[str, Any]]:
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM trade_audit_log WHERE trade_id = ? ORDER BY id ASC",
            (trade_id,),
        )
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
