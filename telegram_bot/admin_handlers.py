from __future__ import annotations

from telegram.ext import CommandHandler

from telegram_bot.keyboards import build_control_panel_keyboard
from telegram_bot.ui_helpers import authorize_update, clear_pending_user_state


def build_admin_handlers(app_services: dict, config_service, admin_chat_id: int):
    """Basic admin/control commands extracted from the legacy Telegram handler file."""

    async def start_command(update, context):
        if not await authorize_update(update, admin_chat_id):
            return
        await update.message.reply_text("Bot online.")

    async def panel_command(update, context):
        if not await authorize_update(update, admin_chat_id):
            return
        await update.message.reply_text("Control Panel", reply_markup=build_control_panel_keyboard())

    async def cancel_command(update, context):
        if not await authorize_update(update, admin_chat_id):
            return
        clear_pending_user_state(context)
        await update.message.reply_text("Canceled.")

    return [
        CommandHandler("start", start_command),
        CommandHandler("panel", panel_command),
        CommandHandler("cancel", cancel_command),
    ]
