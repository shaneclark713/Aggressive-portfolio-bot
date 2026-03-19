from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler, CommandHandler

from .callbacks import handle_trade_callback
from .control_panel_integration import handle_control_panel_callback
from .keyboards import build_control_panel_keyboard


async def start_command(update, context):
    await update.message.reply_text("Bot online. Use /panel for controls.")


async def panel_command(update, context):
    await update.message.reply_text("Control Panel", reply_markup=build_control_panel_keyboard())


async def config_command(update, context, config_service):
    await update.message.reply_text(config_service.get_human_summary())


def _build_strategies_keyboard(config_service) -> InlineKeyboardMarkup:
    states = config_service.get_strategy_states()
    rows = []
    for strategy_name, is_enabled in states.items():
        icon = "🟢" if is_enabled else "⚪"
        rows.append([InlineKeyboardButton(f"{icon} {strategy_name}", callback_data=f"toggle|strategy|{strategy_name}")])
    rows.append([InlineKeyboardButton("⬅ Back", callback_data="cp|back")])
    return InlineKeyboardMarkup(rows)


def _format_filters(config_service) -> str:
    filters = config_service.resolve_filters()
    lines = [f"Preset: {config_service.get_active_preset()}", ""]
    for section, values in filters.items():
        if not isinstance(values, dict):
            continue
        lines.append(f"[{section}]")
        for key, value in values.items():
            lines.append(f"- {key}: {value}")
        lines.append("")
    return "\n".join(lines).strip()


def build_handlers(app_services, config_service, admin_chat_id: int):
    async def _config(update, context):
        await config_command(update, context, config_service)

    async def _guarded_callback(update, context):
        query = update.callback_query
        await query.answer()

        if update.effective_chat.id != admin_chat_id:
            await query.answer("Unauthorized", show_alert=True)
            return

        data = query.data or ""

        if data.startswith(("a|", "p|", "r|")):
            await handle_trade_callback(update, context, app_services)
            return

        if data in {"cp|presets", "cp|mode"} or data.startswith(("cpreset|", "cmode|")):
            await handle_control_panel_callback(update, context, config_service, config_service.settings_repo)
            return

        if data == "cp|back":
            await query.edit_message_text("Control Panel", reply_markup=build_control_panel_keyboard())
            return

        if data == "cp|strategies":
            await query.edit_message_text("Strategies", reply_markup=_build_strategies_keyboard(config_service))
            return

        if data == "cp|filters":
            await query.edit_message_text(
                _format_filters(config_service),
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅ Back", callback_data="cp|back")]]),
            )
            return

        if data == "cp|sell_all":
            trade_repo = app_services["trade_repo"]
            open_trades = trade_repo.get_open_trades()
            if not open_trades:
                await query.edit_message_text(
                    "No open bot positions found.",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅ Back", callback_data="cp|back")]]),
                )
                return

            if config_service.get_execution_mode() == "alerts_only":
                await query.edit_message_text(
                    f"Found {len(open_trades)} open position(s), but execution mode is alerts_only, so no liquidation was sent.",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅ Back", callback_data="cp|back")]]),
                )
                return

            for trade in open_trades:
                trade_repo.update_trade_status(trade["trade_id"], "CLOSED")

            await query.edit_message_text(
                f"Marked {len(open_trades)} position(s) as CLOSED.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅ Back", callback_data="cp|back")]]),
            )
            return

        if data.startswith("toggle|strategy|"):
            strategy_name = data.split("|", 2)[2]
            new_state = config_service.toggle_strategy(strategy_name)
            state_text = "enabled" if new_state else "disabled"
            await query.edit_message_text(
                f"{strategy_name} {state_text}.",
                reply_markup=_build_strategies_keyboard(config_service),
            )
            return

        await query.edit_message_text("Unknown control panel action.", reply_markup=build_control_panel_keyboard())

    return [
        CommandHandler("start", start_command),
        CommandHandler("panel", panel_command),
        CommandHandler("config", _config),
        CommandHandler("status", _config),
        CallbackQueryHandler(_guarded_callback),
    ]
