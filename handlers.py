from telegram.ext import CommandHandler, CallbackQueryHandler

from .callbacks import handle_trade_callback
from .keyboards import build_control_panel_keyboard


async def start_command(update, context):
    await update.message.reply_text('Bot online.')


async def panel_command(update, context):
    await update.message.reply_text('Control Panel', reply_markup=build_control_panel_keyboard())


async def config_command(update, context, config_service):
    await update.message.reply_text(
        f'Preset: {config_service.get_active_preset()}\n'
        f'Mode: {config_service.get_execution_mode()}'
    )


def build_handlers(app_services, config_service, admin_chat_id: int):
    async def _config(update, context):
        await config_command(update, context, config_service)

    async def _guarded_callback(update, context):
        if update.effective_chat.id != admin_chat_id:
            await update.callback_query.answer('Unauthorized', show_alert=True)
            return
        data = update.callback_query.data or ''
        if data.startswith(('a|', 'p|', 'r|')):
            await handle_trade_callback(update, context, app_services)
        else:
            await update.callback_query.answer('Control panel action not fully wired in this handler.')

    return [
        CommandHandler('start', start_command),
        CommandHandler('panel', panel_command),
        CommandHandler('config', _config),
        CallbackQueryHandler(_guarded_callback),
    ]
