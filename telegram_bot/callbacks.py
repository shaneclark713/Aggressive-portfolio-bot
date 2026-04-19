from __future__ import annotations

from typing import Any


async def handle_trade_callback(update, context, app_services):
    query = update.callback_query
    await query.answer()

    raw = query.data or ""
    parts = raw.split("|", 1)
    if len(parts) != 2:
        await query.edit_message_text("Invalid trade action.")
        return

    action, trade_id = parts
    alert_service = app_services.get("alert_service")
    alert_repo = app_services.get("alert_repo")
    trade_repo = app_services.get("trade_repo")
    execution_log_repo = app_services.get("execution_log_repo")

    def _log(event_name: str, **payload: Any) -> None:
        if execution_log_repo is None:
            return
        if hasattr(execution_log_repo, "log_event"):
            execution_log_repo.log_event(event_name, payload)
        elif hasattr(execution_log_repo, "log"):
            execution_log_repo.log(event_name, **payload)

    if action == "a":
        if alert_service is not None and hasattr(alert_service, "approve_alert"):
            alert_service.approve_alert(trade_id)
        else:
            if alert_repo is not None:
                if hasattr(alert_repo, "update_alert_status"):
                    alert_repo.update_alert_status(trade_id, "APPROVED")
                elif hasattr(alert_repo, "update_status"):
                    alert_repo.update_status(trade_id, "APPROVED")
            if trade_repo is not None and hasattr(trade_repo, "upsert_trade"):
                trade_repo.upsert_trade({"trade_id": trade_id, "status": "APPROVED"})
            _log("ALERT_APPROVED", trade_id=trade_id, actor_chat_id=str(update.effective_chat.id))
        await query.edit_message_text(f"Trade {trade_id} approved.")
        return

    if action == "p":
        if alert_service is not None and hasattr(alert_service, "paper_trade_alert"):
            alert_service.paper_trade_alert(trade_id)
        else:
            if alert_repo is not None:
                if hasattr(alert_repo, "update_alert_status"):
                    alert_repo.update_alert_status(trade_id, "PAPER")
                elif hasattr(alert_repo, "update_status"):
                    alert_repo.update_status(trade_id, "PAPER")
            if trade_repo is not None and hasattr(trade_repo, "upsert_trade"):
                trade_repo.upsert_trade({"trade_id": trade_id, "status": "PAPER", "notes": "Paper trade"})
            _log("ALERT_PAPER_TRADED", trade_id=trade_id, actor_chat_id=str(update.effective_chat.id))
        await query.edit_message_text(f"Trade {trade_id} marked as paper trade.")
        return

    if action == "r":
        if alert_service is not None and hasattr(alert_service, "reject_alert"):
            alert_service.reject_alert(trade_id)
        else:
            if alert_repo is not None:
                if hasattr(alert_repo, "update_alert_status"):
                    alert_repo.update_alert_status(trade_id, "REJECTED")
                elif hasattr(alert_repo, "update_status"):
                    alert_repo.update_status(trade_id, "REJECTED")
            if trade_repo is not None and hasattr(trade_repo, "upsert_trade"):
                trade_repo.upsert_trade({"trade_id": trade_id, "status": "REJECTED"})
            _log("ALERT_REJECTED", trade_id=trade_id, actor_chat_id=str(update.effective_chat.id))
        await query.edit_message_text(f"Trade {trade_id} rejected.")
        return

    await query.edit_message_text("Unknown trade action.")
