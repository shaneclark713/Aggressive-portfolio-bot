from __future__ import annotations

import logging

from telegram.ext import CommandHandler

from services.broker_ladder_service import BrokerLadderService
from services.position_sync_service import PositionSyncService
from telegram_bot.formatters import (
    format_exit_ladder_submission,
    format_ladder_execution_result,
    format_ladder_submission,
    format_open_trails,
    format_position_sync_result,
    format_triggered_exit_result,
)

logger = logging.getLogger("aggressive_portfolio_bot.telegram.execution_handlers")


async def _is_authorized(update, admin_chat_id: int) -> bool:
    chat_id = update.effective_chat.id if update.effective_chat else None
    if chat_id == admin_chat_id:
        return True
    logger.warning("Unauthorized execution command from chat_id=%s expected=%s", chat_id, admin_chat_id)
    if update.message:
        await update.message.reply_text("Unauthorized.")
    return False


def _mode(config_service) -> str:
    try:
        return config_service.get_execution_mode()
    except Exception:
        return "alerts_only"


def _parse_rr_targets(args: list[str], index: int):
    if len(args) <= index:
        return None
    return [float(value) for value in args[index].split(",") if value.strip()]


def build_execution_handlers(app_services: dict, config_service, admin_chat_id: int):
    """Execution command group extracted from the legacy Telegram handler file."""

    live_execution_service = app_services.get("live_execution_service")
    trailing_stop_service = app_services.get("trailing_stop_service")
    position_sync_service = app_services.get("position_sync_service") or PositionSyncService(
        trailing_stop_service,
        alpaca_client=app_services.get("alpaca_client"),
        tradier_client=app_services.get("tradier_client"),
    )
    broker_ladder_service = app_services.get("broker_ladder_service") or BrokerLadderService(app_services.get("execution_router"))

    async def trail_status(update, context):
        if not await _is_authorized(update, admin_chat_id):
            return
        if trailing_stop_service is None:
            await update.message.reply_text("Trailing stop service is not configured.")
            return
        await update.message.reply_text(format_open_trails(trailing_stop_service.list_positions()), parse_mode="HTML")

    async def sync_positions(update, context):
        if not await _is_authorized(update, admin_chat_id):
            return
        rows = await position_sync_service.sync_live_positions(include_demo_fallback=True)
        await update.message.reply_text(format_position_sync_result(rows), parse_mode="HTML")

    async def submit_ladder(update, context):
        if not await _is_authorized(update, admin_chat_id):
            return
        if live_execution_service is None:
            await update.message.reply_text("Live execution service not configured.")
            return
        if len(context.args) < 5:
            await update.message.reply_text("Usage: /submit_ladder <symbol> <side> <total_size> <entry_price> <strategy> [mode]")
            return
        symbol, side, total_size, entry_price, strategy = context.args[:5]
        mode = context.args[5] if len(context.args) >= 6 else _mode(config_service)
        plan = await live_execution_service.submit_stock_ladder(
            symbol.upper(), side.upper(), int(total_size), float(entry_price), mode, strategy
        )
        await update.message.reply_text(format_ladder_submission(plan), parse_mode="HTML")

    async def execute_ladder(update, context):
        if not await _is_authorized(update, admin_chat_id):
            return
        if live_execution_service is None:
            await update.message.reply_text("Live execution service not configured.")
            return
        if len(context.args) < 5:
            await update.message.reply_text("Usage: /execute_ladder <symbol> <side> <total_size> <entry_price> <strategy> [mode]")
            return
        symbol, side, total_size, entry_price, strategy = context.args[:5]
        mode = context.args[5] if len(context.args) >= 6 else _mode(config_service)
        plan = await live_execution_service.submit_stock_ladder(
            symbol.upper(), side.upper(), int(total_size), float(entry_price), mode, strategy
        )
        if not plan.get("submit_ready", False):
            await update.message.reply_text(f"Execution blocked: {plan.get('blocked_reason') or 'not submit ready'}", parse_mode="HTML")
            return
        result = await broker_ladder_service.submit_stock_ladder(symbol.upper(), side.upper(), plan["entries"])
        await update.message.reply_text(format_ladder_execution_result(result), parse_mode="HTML")

    async def submit_exit_ladder(update, context):
        if not await _is_authorized(update, admin_chat_id):
            return
        if live_execution_service is None:
            await update.message.reply_text("Live execution service not configured.")
            return
        if len(context.args) < 6:
            await update.message.reply_text("Usage: /submit_exit_ladder <symbol> <side> <total_size> <entry_price> <stop_loss> <strategy> [mode] [rr_targets_csv]")
            return
        symbol, side, total_size, entry_price, stop_loss, strategy = context.args[:6]
        mode = context.args[6] if len(context.args) >= 7 else _mode(config_service)
        rr_targets = _parse_rr_targets(context.args, 7)
        plan = await live_execution_service.submit_exit_ladder(
            symbol.upper(), side.upper(), int(total_size), float(entry_price), float(stop_loss), mode, strategy, rr_targets=rr_targets
        )
        await update.message.reply_text(format_exit_ladder_submission(plan), parse_mode="HTML")

    async def execute_exit_ladder(update, context):
        if not await _is_authorized(update, admin_chat_id):
            return
        if live_execution_service is None:
            await update.message.reply_text("Live execution service not configured.")
            return
        if len(context.args) < 6:
            await update.message.reply_text("Usage: /execute_exit_ladder <symbol> <side> <total_size> <entry_price> <stop_loss> <strategy> [mode] [rr_targets_csv]")
            return
        symbol, side, total_size, entry_price, stop_loss, strategy = context.args[:6]
        mode = context.args[6] if len(context.args) >= 7 else _mode(config_service)
        rr_targets = _parse_rr_targets(context.args, 7)
        plan = await live_execution_service.submit_exit_ladder(
            symbol.upper(), side.upper(), int(total_size), float(entry_price), float(stop_loss), mode, strategy, rr_targets=rr_targets
        )
        result = await broker_ladder_service.submit_exit_ladder(symbol.upper(), plan["exits"])
        await update.message.reply_text(format_ladder_execution_result(result), parse_mode="HTML")

    async def trigger_trails(update, context):
        if not await _is_authorized(update, admin_chat_id):
            return
        if live_execution_service is None:
            await update.message.reply_text("Live execution service not configured.")
            return
        limit_buffer_pct = float(context.args[0]) if context.args else 0.0
        result = await live_execution_service.execute_triggered_trailing_exits(limit_buffer_pct=limit_buffer_pct)
        await update.message.reply_text(format_triggered_exit_result(result), parse_mode="HTML")

    return [
        CommandHandler("trail_status", trail_status),
        CommandHandler("sync_positions", sync_positions),
        CommandHandler("submit_ladder", submit_ladder),
        CommandHandler("execute_ladder", execute_ladder),
        CommandHandler("submit_exit_ladder", submit_exit_ladder),
        CommandHandler("execute_exit_ladder", execute_exit_ladder),
        CommandHandler("trigger_trails", trigger_trails),
    ]
