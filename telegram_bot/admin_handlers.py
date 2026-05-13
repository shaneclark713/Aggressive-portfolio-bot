from __future__ import annotations

import logging

from telegram.ext import CommandHandler

from telegram_bot.keyboards import build_control_panel_keyboard

logger = logging.getLogger("aggressive_portfolio_bot.telegram.admin_handlers")

PENDING_FILTER_EDIT = "pending_filter_edit"
PENDING_EXEC_EDIT = "pending_execution_edit"
PENDING_OPTIONS_EDIT = "pending_options_edit"
PENDING_TICKER_SCAN = "pending_ticker_scan"
PENDING_TICKER_RESEARCH = "pending_ticker_research"
PENDING_KEYS = (
    PENDING_FILTER_EDIT,
    PENDING_EXEC_EDIT,
    PENDING_OPTIONS_EDIT,
    PENDING_TICKER_SCAN,
    PENDING_TICKER_RESEARCH,
)


async def _is_authorized(update, admin_chat_id: int) -> bool:
    chat_id = update.effective_chat.id if update.effective_chat else None
    if chat_id == admin_chat_id:
        return True
    logger.warning("Unauthorized admin command from chat_id=%s expected=%s", chat_id, admin_chat_id)
    if update.message:
        await update.message.reply_text("Unauthorized.")
    return False


def build_admin_handlers(app_services: dict, config_service, admin_chat_id: int):
    """Basic admin/control commands extracted from the legacy Telegram handler file."""

    async def start_command(update, context):
        if not await _is_authorized(update, admin_chat_id):
            return
        await update.message.reply_text("Bot online.")

    async def panel_command(update, context):
        if not await _is_authorized(update, admin_chat_id):
            return
        await update.message.reply_text("Control Panel", reply_markup=build_control_panel_keyboard())

    async def cancel_command(update, context):
        if not await _is_authorized(update, admin_chat_id):
            return
        for key in PENDING_KEYS:
            context.user_data.pop(key, None)
        await update.message.reply_text("Canceled.")

    return [
        CommandHandler("start", start_command),
        CommandHandler("panel", panel_command),
        CommandHandler("cancel", cancel_command),
    ]
