from __future__ import annotations


async def handle_trade_callback(update, context, app_services):
    query = update.callback_query
    await query.answer()

    data = (query.data or "").split("|")
    if len(data) < 2:
        await query.edit_message_text("Invalid trade action.")
        return

    action, trade_id = data[0], data[1]
    alert_repo = app_services["alert_repo"]
    trade_repo = app_services["trade_repo"]
    exec_log = app_services["execution_log_repo"]

    if action == "a":
        alert_repo.update_status(trade_id, "APPROVED")
        trade_repo.upsert_trade({"trade_id": trade_id, "status": "APPROVED"})
        exec_log.log("APPROVED", trade_id=trade_id, actor_chat_id=str(update.effective_chat.id))
        await query.edit_message_text(f"Trade {trade_id} approved.")
    elif action == "p":
        alert_repo.update_status(trade_id, "APPROVED")
        trade_repo.upsert_trade({"trade_id": trade_id, "status": "APPROVED", "notes": "Paper trade"})
        exec_log.log("PAPER_APPROVED", trade_id=trade_id, actor_chat_id=str(update.effective_chat.id))
        await query.edit_message_text(f"Trade {trade_id} marked as paper trade.")
    elif action == "r":
        alert_repo.update_status(trade_id, "REJECTED")
        trade_repo.upsert_trade({"trade_id": trade_id, "status": "REJECTED"})
        exec_log.log("REJECTED", trade_id=trade_id, actor_chat_id=str(update.effective_chat.id))
        await query.edit_message_text(f"Trade {trade_id} rejected.")
    else:
        await query.edit_message_text("Unknown trade action.")
