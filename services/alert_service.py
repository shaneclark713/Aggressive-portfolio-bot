from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from core.utils import new_trade_id


class AlertService:
    def __init__(self, alert_repo, trade_repo, execution_log_repo, config_service, settings):
        self.alert_repo = alert_repo
        self.trade_repo = trade_repo
        self.execution_log_repo = execution_log_repo
        self.config_service = config_service
        self.settings = settings

    def create_trade_candidate(self, payload: dict, broker: str, instrument_type: str) -> str:
        trade_id = new_trade_id()
        expires_at = datetime.now(ZoneInfo('America/New_York')) + timedelta(seconds=self.settings.bot_approval_timeout_seconds)
        self.alert_repo.create_alert(
            trade_id,
            payload['symbol'],
            payload['strategy'],
            payload['side'],
            self.config_service.get_execution_mode(),
            expires_at.strftime('%Y-%m-%d %H:%M:%S'),
        )
        self.trade_repo.upsert_trade({
            'trade_id': trade_id,
            'broker': broker,
            'broker_order_id': None,
            'symbol': payload['symbol'],
            'side': payload['side'],
            'strategy': payload['strategy'],
            'horizon': payload['trade_horizon'],
            'instrument_type': instrument_type,
            'status': 'PENDING_ALERT',
            'entry_time': None,
            'exit_time': None,
            'entry_price': payload['entry_price'],
            'exit_price': None,
            'stop_loss': payload['stop_loss'],
            'take_profit': payload['take_profit'],
            'pnl': None,
            'rr_ratio': payload['rr_ratio'],
            'close_reason': None,
            'entry_snapshot_path': None,
            'close_snapshot_path': None,
            'notes': None,
        })
        self.execution_log_repo.log('ALERT_CREATED', trade_id=trade_id, details=payload)
        return trade_id

    def expire_alerts(self):
        expired = self.alert_repo.get_expired_alerts()
        ids = []
        for row in expired:
            self.alert_repo.update_status(row['trade_id'], 'EXPIRED')
            self.trade_repo.upsert_trade({'trade_id': row['trade_id'], 'status': 'EXPIRED'})
            self.execution_log_repo.log('ALERT_EXPIRED', trade_id=row['trade_id'])
            ids.append(row['trade_id'])
        return ids
