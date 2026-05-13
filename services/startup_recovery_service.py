from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

logger = logging.getLogger("aggressive_portfolio_bot.services.startup_recovery")


class StartupRecoveryService:
    """Reconcile broker positions, trailing state, and database state at startup.

    This service is safety-oriented and does not place orders. Broker positions are
    treated as the source of truth for what is actually open.
    """

    def __init__(self, position_sync_service, trade_repo, execution_log_repo=None):
        self.position_sync_service = position_sync_service
        self.trade_repo = trade_repo
        self.execution_log_repo = execution_log_repo

    async def recover(self, prune_missing: bool = True) -> dict[str, Any]:
        started_at = datetime.utcnow().isoformat()
        payload: dict[str, Any] = {
            "started_at": started_at,
            "recovered_trade_ids": [],
            "live_symbols": [],
            "closed_missing_trade_ids": [],
            "errors": [],
        }
        try:
            sync_results = await self.position_sync_service.sync_live_positions(
                prune_missing=True,
                include_demo_fallback=False,
            )
            payload["sync_results"] = self._compact_sync_results(sync_results)
            live_positions = self._extract_live_positions(sync_results)
            live_symbols = {str(pos.get("symbol") or "").upper() for pos in live_positions if pos.get("symbol")}
            payload["live_symbols"] = sorted(live_symbols)
            for position in live_positions:
                try:
                    trade_id = self.trade_repo.upsert_recovered_trade(position)
                    payload["recovered_trade_ids"].append(trade_id)
                except Exception as exc:
                    error = {"position_id": position.get("position_id"), "error": str(exc)}
                    payload["errors"].append(error)
                    logger.warning("Failed to upsert recovered trade: %s", error)
            if prune_missing:
                payload["closed_missing_trade_ids"] = self.trade_repo.mark_missing_open_trades_reconciled(live_symbols)
            payload["completed_at"] = datetime.utcnow().isoformat()
            payload["status"] = "completed_with_errors" if payload["errors"] else "completed"
            self._log("startup_recovery_completed", payload)
            return payload
        except Exception as exc:
            payload["completed_at"] = datetime.utcnow().isoformat()
            payload["status"] = "failed"
            payload["errors"].append({"error": str(exc)})
            self._log("startup_recovery_failed", payload)
            logger.exception("Startup recovery failed: %s", exc)
            return payload

    def _extract_live_positions(self, sync_results: dict[str, Any]) -> list[dict[str, Any]]:
        positions: list[dict[str, Any]] = []
        for key, value in (sync_results or {}).items():
            if not isinstance(value, dict):
                continue
            if key.endswith("_error") or key == "pruned_positions":
                continue
            symbol = value.get("symbol")
            if not symbol:
                continue
            positions.append(
                {
                    "position_id": value.get("position_id") or key,
                    "symbol": symbol,
                    "broker": value.get("broker") or self._infer_broker(key),
                    "side": value.get("side") or "LONG",
                    "quantity": value.get("quantity"),
                    "entry_price": value.get("entry_price"),
                    "current_price": value.get("current_price"),
                    "stop_loss": value.get("stop_loss"),
                    "asset_type": value.get("asset_type"),
                    "metadata": value.get("metadata") or {},
                }
            )
        return positions

    def _infer_broker(self, position_id: str) -> str:
        if str(position_id).startswith("alpaca:"):
            return "alpaca"
        if str(position_id).startswith("tradier:"):
            return "tradier"
        return "unknown"

    def _compact_sync_results(self, sync_results: dict[str, Any]) -> dict[str, Any]:
        compact: dict[str, Any] = {}
        for key, value in (sync_results or {}).items():
            if isinstance(value, dict):
                compact[key] = {
                    "symbol": value.get("symbol"),
                    "broker": value.get("broker"),
                    "side": value.get("side"),
                    "quantity": value.get("quantity"),
                    "entry_price": value.get("entry_price"),
                    "current_price": value.get("current_price"),
                    "stop_loss": value.get("stop_loss"),
                    "asset_type": value.get("asset_type"),
                    "error": value.get("error"),
                    "removed": value.get("removed"),
                    "count": value.get("count"),
                }
            else:
                compact[key] = value
        return compact

    def _log(self, event_type: str, payload: dict[str, Any]) -> None:
        if self.execution_log_repo is None:
            return
        try:
            self.execution_log_repo.log_event(event_type, payload)
        except Exception as exc:
            logger.warning("Failed to write startup recovery audit log: %s", exc)
