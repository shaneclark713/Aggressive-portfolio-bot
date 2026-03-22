from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler, CommandHandler, MessageHandler, filters

from .callbacks import handle_trade_callback
from .keyboards import (
    VALID_FILTER_CATEGORIES,
    build_control_panel_keyboard,
    build_filter_categories_keyboard,
    build_filter_fields_keyboard,
    build_mode_keyboard,
    build_presets_keyboard,
    build_strategies_keyboard,
)
from .formatters import format_scan_status


def _format_filter_category(category: str, values: dict) -> str:
    lines = [f"{category.title()} Filters", ""]
    for key, value in values.items():
        lines.append(f"- {key}: {value}")
    lines.append("")
    lines.append("Tap a field below to edit it.")
    return "\n".join(lines)


async def start_command(update, context):
    await update.message.reply_text("Bot online.")


async def panel_command(update, context):
    await update.message.reply_text("Control Panel", reply_markup=build_control_panel_keyboard())


async def config_command(update, context, config_service):
    await update.message.reply_text(
        f"Preset: {config_service.get_active_preset()}\n"
        f"Mode: {config_service.get_execution_mode()}"
    )


async def cancel_command(update, context):
    context.user_data.pop("pending_filter_edit", None)
    await update.message.reply_text("Canceled.")


def build_handlers(app_services, config_service, admin_chat_id: int):
    async def _config(update, context):
        await config_command(update, context, config_service)

    async def _scan(update, context):
        if update.effective_chat.id != admin_chat_id:
            await update.message.reply_text("Unauthorized.")
            return
        scanner = app_services.get("scanner")
        if scanner is None:
            await update.message.reply_text("Scanner service not available.")
            return
        await update.message.reply_text("Running manual scan...")
        candidates = await scanner.scan_day_trade_candidates()
        stats = scanner.get_last_scan_stats()
        await update.message.reply_text(
            format_scan_status(stats) + f"\n\nCandidates returned: {len(candidates)}",
            parse_mode="HTML",
        )

    async def _scan_status(update, context):
        if update.effective_chat.id != admin_chat_id:
            await update.message.reply_text("Unauthorized.")
            return
        scanner = app_services.get("scanner")
        if scanner is None:
            await update.message.reply_text("Scanner service not available.")
            return
        await update.message.reply_text(
            format_scan_status(scanner.get_last_scan_stats()),
            parse_mode="HTML",
        )

    async def _pending_text(update, context):
        pending = context.user_data.get("pending_filter_edit")
        if not pending:
            return

        if update.effective_chat.id != admin_chat_id:
            await update.message.reply_text("Unauthorized.")
            context.user_data.pop("pending_filter_edit", None)
            return

        raw_value = (update.message.text or "").strip()
        category = pending["category"]
        field = pending["field"]

        try:
            new_value = config_service.set_filter_value(category, field, raw_value)
        except ValueError as exc:
            await update.message.reply_text(
                f"Invalid value for {category}.{field}: {exc}\nSend a new value or /cancel."
            )
            return
        except Exception as exc:
            await update.message.reply_text(
                f"Could not update {category}.{field}: {exc}\nSend /cancel to exit."
            )
            return

        context.user_data.pop("pending_filter_edit", None)
        values = config_service.get_filter_fields(category)
        await update.message.reply_text(
            f"Updated {category}.{field} to {new_value}.",
            reply_markup=build_filter_fields_keyboard(category, values),
        )

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
            context.user_data.pop("pending_filter_edit", None)
            await query.edit_message_text("Control Panel", reply_markup=build_control_panel_keyboard())
            return

        if data == "cp|presets":
            await query.edit_message_text(
                f"Select Preset\nCurrent: {config_service.get_active_preset()}",
                reply_markup=build_presets_keyboard(
                    config_service.get_available_presets(),
                    config_service.get_active_preset(),
                ),
            )
            return

        if data == "cp|mode":
            await query.edit_message_text(
                f"Select Mode\nCurrent: {config_service.get_execution_mode()}",
                reply_markup=build_mode_keyboard(config_service.get_execution_mode()),
            )
            return

        if data == "cp|strategies":
            await query.edit_message_text(
                "Strategies",
                reply_markup=build_strategies_keyboard(config_service.get_strategy_states()),
            )
            return

        if data == "cp|filters":
            filters_snapshot = config_service.resolve_filters()
            await query.edit_message_text(
                "Choose a filter category to edit.",
                reply_markup=build_filter_categories_keyboard(
                    filters_snapshot,
                    config_service.get_active_preset(),
                ),
            )
            return

        if data.startswith("fcat|"):
            category = data.split("|", 1)[1].lower()
            if category not in VALID_FILTER_CATEGORIES:
                await query.answer("Invalid filter category.", show_alert=True)
                return
            values = config_service.get_filter_fields(category)
            context.user_data.pop("pending_filter_edit", None)
            await query.edit_message_text(
                _format_filter_category(category, values),
                reply_markup=build_filter_fields_keyboard(category, values),
            )
            return

        if data.startswith("fedit|"):
            _, category, field = data.split("|", 2)
            category = category.lower()
            if category not in VALID_FILTER_CATEGORIES:
                await query.answer("Invalid filter category.", show_alert=True)
                return
            current_value = config_service.get_filter_value(category, field)
            context.user_data["pending_filter_edit"] = {"category": category, "field": field}
            await query.message.reply_text(
                f"Send new value for {category}.{field}\nCurrent: {current_value}\nUse /cancel to stop."
            )
            return

        if data == "freset|all":
            config_service.reset_filter_overrides()
            context.user_data.pop("pending_filter_edit", None)
            await query.edit_message_text(
                "All filter overrides cleared.",
                reply_markup=build_filter_categories_keyboard(
                    config_service.resolve_filters(),
                    config_service.get_active_preset(),
                ),
            )
            return

        if data.startswith("freset|"):
            category = data.split("|", 1)[1].lower()
            if category not in VALID_FILTER_CATEGORIES:
                await query.answer("Invalid filter category.", show_alert=True)
                return
            config_service.reset_filter_overrides(category=category)
            values = config_service.get_filter_fields(category)
            context.user_data.pop("pending_filter_edit", None)
            await query.edit_message_text(
                f"Reset {category} overrides.",
                reply_markup=build_filter_fields_keyboard(category, values),
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
                reply_markup=build_strategies_keyboard(config_service.get_strategy_states()),
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
        CommandHandler("scan", _scan),
        CommandHandler("scan_status", _scan_status),
        CommandHandler("cancel", cancel_command),
        MessageHandler(filters.TEXT & ~filters.COMMAND, _pending_text),
        CallbackQueryHandler(_guarded_callback),
        ]
