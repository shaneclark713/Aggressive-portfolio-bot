from __future__ import annotations

from typing import Any


class SpyAutonomyService:
    """Controlled live-only autonomy gate for SPY/XSP 0DTE workflows.

    This service never bypasses risk checks, execution guards, or execution mode.
    It only attempts execution when mode is exactly `live`, the setup passes A+ gates,
    and a concrete option contract is provided by the upstream scanner/selector.
    """

    def __init__(
        self,
        config_service=None,
        spy_0dte_service=None,
        spy_setup_score_service=None,
        live_execution_service=None,
        execution_log_repo=None,
    ):
        self.config_service = config_service
        self.spy_0dte_service = spy_0dte_service
        self.spy_setup_score_service = spy_setup_score_service
        self.live_execution_service = live_execution_service
        self.execution_log_repo = execution_log_repo

    async def evaluate(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        mode = self._execution_mode()
        if mode != "live":
            return self._blocked("execution mode is not live", mode=mode)
        if self.spy_setup_score_service is None:
            return self._blocked("SPY setup scorer is not configured", mode=mode)
        if self.live_execution_service is None:
            return self._blocked("live execution service is not configured", mode=mode)

        scan_payload = payload
        if scan_payload is None:
            if self.spy_0dte_service is None:
                return self._blocked("SPY 0DTE service is not configured", mode=mode)
            scan_payload = await self.spy_0dte_service.analyze()

        gate = self.spy_setup_score_service.a_plus_filter(scan_payload)
        if not gate.get("eligible"):
            decision = {
                "status": "blocked",
                "mode": mode,
                "reason": "setup did not pass strict A+ gate",
                "gate": gate,
            }
            self._log("SPY_AUTONOMY_BLOCKED", decision)
            return decision

        contract = self._contract_from_payload(scan_payload)
        if not contract:
            decision = {
                "status": "blocked",
                "mode": mode,
                "reason": "no concrete option contract selected",
                "gate": gate,
                "required_payload_keys": ["option_symbol", "recommended_option_symbol", "selected_contract.option_symbol"],
            }
            self._log("SPY_AUTONOMY_BLOCKED", decision)
            return decision

        quantity = int(scan_payload.get("quantity") or scan_payload.get("contracts") or 1)
        side = str(scan_payload.get("side") or scan_payload.get("option_side") or "buy").lower()
        order_type = str(scan_payload.get("order_type") or "market").lower()
        price = scan_payload.get("limit_price") or scan_payload.get("price")

        decision = {
            "status": "ready",
            "mode": mode,
            "symbol": str(scan_payload.get("symbol") or "SPY").upper(),
            "option_symbol": contract,
            "side": side,
            "quantity": quantity,
            "order_type": order_type,
            "price": price,
            "gate": gate,
        }
        self._log("SPY_AUTONOMY_READY", decision)
        return decision

    async def execute_if_live(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        decision = await self.evaluate(payload)
        if decision.get("status") != "ready":
            return decision
        result = await self.live_execution_service.submit_single_option(
            symbol=decision["symbol"],
            option_symbol=decision["option_symbol"],
            side=decision["side"],
            quantity=decision["quantity"],
            order_type=decision["order_type"],
            price=decision.get("price"),
        )
        final = {**decision, "status": "submitted", "result": result}
        self._log("SPY_AUTONOMY_SUBMITTED", final)
        return final

    def _execution_mode(self) -> str:
        if self.config_service is None:
            return "unknown"
        try:
            return str(self.config_service.get_execution_mode()).strip().lower()
        except Exception:
            return "unknown"

    def _contract_from_payload(self, payload: dict[str, Any]) -> str | None:
        for key in ("option_symbol", "recommended_option_symbol", "selected_option_symbol"):
            value = payload.get(key)
            if value:
                return str(value).strip()
        selected = payload.get("selected_contract") or payload.get("contract") or {}
        if isinstance(selected, dict):
            value = selected.get("option_symbol") or selected.get("symbol")
            if value:
                return str(value).strip()
        return None

    def _blocked(self, reason: str, mode: str = "unknown") -> dict[str, Any]:
        decision = {"status": "blocked", "mode": mode, "reason": reason}
        self._log("SPY_AUTONOMY_BLOCKED", decision)
        return decision

    def _log(self, event_type: str, payload: dict[str, Any]) -> None:
        if self.execution_log_repo is None:
            return
        try:
            if hasattr(self.execution_log_repo, "log_event"):
                self.execution_log_repo.log_event(event_type, payload)
            elif hasattr(self.execution_log_repo, "log"):
                self.execution_log_repo.log(event_type, **payload)
        except Exception:
            return
