from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler

from .callbacks import handle_trade_callback
from .keyboards import build_control_panel_keyboard


def _build_presets_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Day Trade Momentum", callback_data="set|preset|day_trade_momentum"),
            ],
            [
                InlineKeyboardButton("Swing Trade", callback_data="set|preset|swing_trade"),
            ],
            [
                InlineKeyboardButton("⬅ Back", callback_data="cp|back"),
            ],
        ]
    )


def _build_mode_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Alerts Only", callback_data="set|mode|alerts_only"),
            ],
            [
                InlineKeyboardButton("Paper", callback_data="set|mode|paper"),
            ],
            [
                InlineKeyboardButton("Live", callback_data="set|mode|live"),
            ],
            [
                InlineKeyboardButton("⬅ Back", callback_data="cp|back"),
            ],
        ]
    )


def _build_strategies_keyboard(config_service) -> InlineKeyboardMarkup:
    states = config_service.get_strategy_states()
    rows = []

    for strategy_name, is_enabled in states.items():
        icon = "🟢" if is_enabled else "⚪"
        rows.append(
            [
                InlineKeyboardButton(
                    f"{icon} {strategy_name}",
                    callback_data=f"toggle|strategy|{strategy_name}",
                )
            ]
        )

    rows.append([InlineKeyboardButton("⬅ Back", callback_data="cp|back")])
    return InlineKeyboardMarkup(rows)


def _format_filters(config_service) -> str:
    filters = config_service.resolve_filters()
    lines = ["Current Filters"]

    for section, values in filters.items():
        lines.append(f"\n[{section}]")
        if isinstance(values, dict):
            for key, value in values.items():
                lines.append(f"- {key}: {value}")
        else:
            lines.append(f"- {values}")

    return "\n".join(lines)


async def start_command(update, context):
    await update.message.reply_text("Bot online.")


async def panel_command(update, context):
    await update.message.reply_text(
        "Control Panel",
        reply_markup=build_control_panel_keyboard(),
    )


async def config_command(update, context, config_service):
    await update.message.reply_text(
        f"Preset: {config_service.get_active_preset()}\n"
        f"Mode: {config_service.get_execution_mode()}"
    )


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

        if data == "cp|back":
            await query.edit_message_text(
                "Control Panel",
                reply_markup=build_control_panel_keyboard(),
            )
            return

        if data == "cp|presets":
            await query.edit_message_text(
                f"Select Preset\nCurrent: {config_service.get_active_preset()}",
                reply_markup=_build_presets_keyboard(),
            )
            return

        if data == "cp|mode":
            await query.edit_message_text(
                f"Select Mode\nCurrent: {config_service.get_execution_mode()}",
                reply_markup=_build_mode_keyboard(),
            )
            return

        if data == "cp|strategies":
            await query.edit_message_text(
                "Strategies",
                reply_markup=_build_strategies_keyboard(config_service),
            )
            return

        if data == "cp|filters":
            await query.edit_message_text(
                _format_filters(config_service),
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("⬅ Back", callback_data="cp|back")]]
                ),
            )
            return

        if data == "cp|sell_all":
            trade_repo = app_services["trade_repo"]
            open_trades = trade_repo.get_open_trades()

            if not open_trades:
                await query.edit_message_text(
                    "No open bot positions found.",
                    reply_markup=InlineKeyboardMarkup(
                        [[InlineKeyboardButton("⬅ Back", callback_data="cp|back")]]
                    ),
                )
                return

            mode = config_service.get_execution_mode()
            if mode == "alerts_only":
                await query.edit_message_text(
                    f"Found {len(open_trades)} open position(s), but execution mode is alerts_only, so no liquidation was sent.",
                    reply_markup=InlineKeyboardMarkup(
                        [[InlineKeyboardButton("⬅ Back", callback_data="cp|back")]]
                    ),
                )
                return

            for trade in open_trades:
                trade_repo.update_trade_status(trade["trade_id"], "CLOSED")

            await query.edit_message_text(
                f"Marked {len(open_trades)} position(s) as CLOSED.",
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("⬅ Back", callback_data="cp|back")]]
                ),
            )
            return

        if data.startswith("set|preset|"):
            preset_name = data.split("|", 2)[2]
            config_service.set_active_preset(preset_name)
            await query.edit_message_text(
                f"Preset updated to: {preset_name}",
                reply_markup=build_control_panel_keyboard(),
            )
            return

        if data.startswith("set|mode|"):
            mode = data.split("|", 2)[2]
            config_service.set_execution_mode(mode)
            await query.edit_message_text(
                f"Execution mode updated to: {mode}",
                reply_markup=build_control_panel_keyboard(),
            )
            return

        if data.startswith("toggle|strategy|"):
            strategy_name = data.split("|", 2)[2]
            states = config_service.get_strategy_states()
            current = bool(states.get(strategy_name, True))
            config_service.settings_repo.set_strategy_state(strategy_name, not current)

            await query.edit_message_text(
                "Strategies updated",
                reply_markup=_build_strategies_keyboard(config_service),
            )
            return

        await query.edit_message_text(
            "Unknown control panel action.",
            reply_markup=build_control_panel_keyboard(),
        )

    return [
        CommandHandler("start", start_command),
        CommandHandler("panel", panel_command),
        CommandHandler("config", _config),
        CommandHandler("status", _config),
        CallbackQueryHandler(_guarded_callback),
            ]
