from __future__ import annotations

from datetime import datetime
from typing import Any, Dict


class AlertService:
    def __init__(
        self,
        alert_repo,
        trade_repo,
        execution_log_repo,
        config_service,
        settings,
        execution_router=None,
    ):
        self.alert_repo = alert_repo
        self.trade_repo = trade_repo
        self.execution_log_repo = execution_log_repo
        self.config_service = config_service
        self.settings = settings
        self.execution_router = execution_router

    def _default_broker_for_payload(self, instrument_type: str) -> str:
        return "TRADIER" if instrument_type.lower() == "option" else "ALPACA"

    def _build_execution_trade(self, payload: Dict[str, Any], broker: str, instrument_type: str) -> Dict[str, Any]:
        side = str(payload.get("side") or "buy").lower()
        quantity = int(payload.get("quantity") or payload.get("qty") or 1)

        trade: Dict[str, Any] = {
            "type": "option" if instrument_type.lower() == "option" else "stock",
            "symbol": payload["symbol"],
            "qty": max(quantity, 1),
            "side": side,
            "broker": broker,
            "strategy": payload.get("strategy"),
        }

        if instrument_type.lower() == "option":
            trade["option_symbol"] = payload.get("option_symbol")
            if not trade["option_symbol"]:
                raise ValueError("Option payload missing option_symbol")

        return trade

    async def _execute_alert_if_enabled(self, alert_id: int, payload: Dict[str, Any]) -> None:
        mode = self.config_service.get_execution_mode()
        if mode == "alerts_only" or self.execution_router is None:
            return

        instrument_type = (payload.get("instrument_type") or "stock").lower()
        broker = (payload.get("broker") or self._default_broker_for_payload(instrument_type)).upper()
        trade_request = self._build_execution_trade(payload, broker, instrument_type)

        try:
            response = await self.execution_router.execute(trade_request)
            status = "PAPER" if mode == "paper" else "EXECUTED"
            self.alert_repo.update_alert_status(alert_id, status)
            self.execution_log_repo.log_event(
                "ORDER_SUBMITTED",
                {
                    "alert_id": alert_id,
                    "broker": broker,
                    "mode": mode,
                    "symbol": payload.get("symbol"),
                    "strategy": payload.get("strategy"),
                    "side": payload.get("side"),
                    "quantity": trade_request["qty"],
                    "response": response,
                    "submitted_at": datetime.utcnow().isoformat(),
                },
            )
        except Exception as exc:
            self.alert_repo.update_alert_status(alert_id, "EXECUTION_FAILED")
            self.execution_log_repo.log_event(
                "ORDER_SUBMIT_FAILED",
                {
                    "alert_id": alert_id,
                    "broker": broker,
                    "mode": mode,
                    "symbol": payload.get("symbol"),
                    "strategy": payload.get("strategy"),
                    "error": str(exc),
                    "failed_at": datetime.utcnow().isoformat(),
                },
            )

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

    async def create_trade_candidate(
        self,
        payload: Dict[str, Any],
        broker: str | None = None,
        instrument_type: str = "stock",
    ) -> int:
        selected_broker = broker or self._default_broker_for_payload(instrument_type)
        enriched_payload = {
            **payload,
            "broker": selected_broker,
            "instrument_type": instrument_type,
            "mode": self.config_service.get_execution_mode(),
            "created_at": datetime.utcnow().isoformat(),
        }
        alert_id = self.create_alert(enriched_payload)
        await self._execute_alert_if_enabled(alert_id, enriched_payload)
        return alert_id

    def approve_alert(self, alert_id: int) -> None:
        self.alert_repo.update_alert_status(alert_id, "APPROVED")
        self.execution_log_repo.log_event(
            "ALERT_APPROVED",
            {"alert_id": alert_id, "approved_at": datetime.utcnow().isoformat()},
        )

    def reject_alert(self, alert_id: int) -> None:
        self.alert_repo.update_alert_status(alert_id, "REJECTED")
        self.execution_log_repo.log_event(
            "ALERT_REJECTED",
            {"alert_id": alert_id, "rejected_at": datetime.utcnow().isoformat()},
        )

    def paper_trade_alert(self, alert_id: int) -> None:
        self.alert_repo.update_alert_status(alert_id, "PAPER")
        self.execution_log_repo.log_event(
            "ALERT_PAPER_TRADED",
            {"alert_id": alert_id, "paper_traded_at": datetime.utcnow().isoformat()},
        )

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
