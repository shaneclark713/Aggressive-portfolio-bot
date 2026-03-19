from __future__ import annotations

from datetime import datetime
from typing import Any, Dict


class AlertService:
    def __init__(self, alert_repo, trade_repo, execution_log_repo, config_service, settings):
        self.alert_repo = alert_repo
        self.trade_repo = trade_repo
        self.execution_log_repo = execution_log_repo
        self.config_service = config_service
        self.settings = settings

    def create_alert(self, payload: Dict[str, Any]) -> int:
        alert_id = self.alert_repo.create_alert(payload)
        self.execution_log_repo.log_event(
            "ALERT_CREATED",
            {
                "alert_id": alert_id,
                "symbol": payload.get("symbol"),
                "strategy": payload.get("strategy"),
                "side": payload.get("side"),
                "mode": self.config_service.get_execution_mode(),
                "created_at": datetime.utcnow().isoformat(),
            },
        )
        return alert_id

    def create_trade_candidate(self, payload: Dict[str, Any], broker: str, instrument_type: str) -> int:
        enriched_payload = {
            **payload,
            "broker": broker,
            "instrument_type": instrument_type,
            "mode": self.config_service.get_execution_mode(),
            "created_at": datetime.utcnow().isoformat(),
        }
        return self.create_alert(enriched_payload)

    def approve_alert(self, alert_id: int) -> None:
        self.alert_repo.update_alert_status(alert_id, "APPROVED")
        self.execution_log_repo.log_event("ALERT_APPROVED", {"alert_id": alert_id, "approved_at": datetime.utcnow().isoformat()})

    def reject_alert(self, alert_id: int) -> None:
        self.alert_repo.update_alert_status(alert_id, "REJECTED")
        self.execution_log_repo.log_event("ALERT_REJECTED", {"alert_id": alert_id, "rejected_at": datetime.utcnow().isoformat()})

    def paper_trade_alert(self, alert_id: int) -> None:
        self.alert_repo.update_alert_status(alert_id, "PAPER")
        self.execution_log_repo.log_event("ALERT_PAPER_TRADED", {"alert_id": alert_id, "paper_traded_at": datetime.utcnow().isoformat()})

    def expire_alerts(self) -> None:
        timeout_seconds = getattr(self.settings, "bot_approval_timeout_seconds", 180)
        expired = self.alert_repo.get_expired_alerts(timeout_seconds=timeout_seconds)

        for alert in expired:
            self.alert_repo.mark_alert_expired(alert["alert_id"])
            self.execution_log_repo.log_event(
                "ALERT_EXPIRED",
                {
                    "alert_id": alert["alert_id"],
                    "symbol": alert.get("symbol"),
                    "strategy": alert.get("strategy"),
                    "expired_at": datetime.utcnow().isoformat(),
                },
            )
