from __future__ import annotations


async def handle_trade_callback(update, context, app_services):
    query = update.callback_query
    await query.answer()

    data = (query.data or "").split("|")
    if len(data) != 2:
        await query.edit_message_text("Malformed trade action.")
        return

    action, alert_id = data[0], data[1]
    alert_repo = app_services["alert_repo"]
    execution_log_repo = app_services["execution_log_repo"]

    if action == "a":
        alert_repo.update_alert_status(int(alert_id), "APPROVED")
        execution_log_repo.log_event("APPROVED", {"alert_id": alert_id, "actor_chat_id": str(update.effective_chat.id)})
        await query.edit_message_text(f"Alert {alert_id} approved.")
        return

    if action == "p":
        alert_repo.update_alert_status(int(alert_id), "PAPER")
        execution_log_repo.log_event("PAPER_APPROVED", {"alert_id": alert_id, "actor_chat_id": str(update.effective_chat.id)})
        await query.edit_message_text(f"Alert {alert_id} marked as paper trade.")
        return

    if action == "r":
        alert_repo.update_alert_status(int(alert_id), "REJECTED")
        execution_log_repo.log_event("REJECTED", {"alert_id": alert_id, "actor_chat_id": str(update.effective_chat.id)})
        await query.edit_message_text(f"Alert {alert_id} rejected.")
        return

    await query.edit_message_text("Unknown trade action.")
