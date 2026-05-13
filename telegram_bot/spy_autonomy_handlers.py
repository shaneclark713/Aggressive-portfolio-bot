from __future__ import annotations

import logging
from typing import Any

from services.spy_autonomy_service import SpyAutonomyService
from telegram.ext import CommandHandler

from telegram_bot.ui_helpers import authorize_update

logger = logging.getLogger("aggressive_portfolio_bot.telegram.spy_autonomy")


def format_autonomy_decision(decision: dict[str, Any]) -> str:
    status = decision.get("status", "unknown")
    lines = [
        "<b>SPY/XSP Controlled Autonomy</b>",
        "",
        f"• Status: {status}",
        f"• Mode: {decision.get('mode', 'unknown')}",
    ]
    if decision.get("reason"):
        lines.append(f"• Reason: {decision.get('reason')}")
    if decision.get("symbol"):
        lines.append(f"• Symbol: {decision.get('symbol')}")
    if decision.get("option_symbol"):
        lines.append(f"• Option Contract: {decision.get('option_symbol')}")
    if decision.get("quantity"):
        lines.append(f"• Quantity: {decision.get('quantity')}")
    if decision.get("order_type"):
        lines.append(f"• Order Type: {decision.get('order_type')}")
    gate = decision.get("gate") or {}
    if gate:
        lines.extend([
            "",
            "<b>A+ Gate</b>",
            f"• Label: {gate.get('label', 'n/a')}",
            f"• Eligible: {gate.get('eligible', False)}",
        ])
        score = gate.get("score") or {}
        if score:
            lines.append(f"• Score: {score.get('score', 0)} / 100 ({score.get('grade', 'n/a')})")
        blockers = gate.get("blockers", []) or []
        if blockers:
            lines.extend(["", "<b>Blockers</b>"])
            lines.extend(f"• {item}" for item in blockers[:6])
        triggers = gate.get("required_price_triggers", []) or []
        if triggers:
            lines.extend(["", "<b>Required Triggers</b>"])
            lines.extend(f"• {item}" for item in triggers[:6])
    result = decision.get("result")
    if result:
        lines.extend(["", "<b>Execution Result</b>", f"• {result}"])
    lines.extend([
        "",
        "<i>Live-only path. Existing risk service and execution guard still apply.</i>",
    ])
    return "\n".join(lines)


def build_spy_autonomy_handlers(app_services: dict, config_service, admin_chat_id: int):
    """Live-only controlled autonomy commands for Phase 6."""

    def _service():
        return app_services.get("spy_autonomy_service") or SpyAutonomyService(
            config_service=config_service,
            spy_0dte_service=app_services.get("spy_0dte_service"),
            spy_setup_score_service=app_services.get("spy_setup_score_service"),
            live_execution_service=app_services.get("live_execution_service"),
            execution_log_repo=app_services.get("execution_log_repo"),
        )

    async def spy_autonomy_check_command(update, context):
        if not await authorize_update(update, admin_chat_id):
            return
        service = _service()
        try:
            decision = await service.evaluate()
            await update.message.reply_text(format_autonomy_decision(decision), parse_mode="HTML")
        except Exception as exc:
            logger.exception("SPY autonomy check failed: %s", exc)
            await update.message.reply_text(f"SPY autonomy check failed: {type(exc).__name__}: {exc}")

    async def spy_autonomy_execute_command(update, context):
        if not await authorize_update(update, admin_chat_id):
            return
        service = _service()
        try:
            decision = await service.execute_if_live()
            await update.message.reply_text(format_autonomy_decision(decision), parse_mode="HTML")
        except Exception as exc:
            logger.exception("SPY autonomy execute failed: %s", exc)
            await update.message.reply_text(f"SPY autonomy execute failed: {type(exc).__name__}: {exc}")

    return [
        CommandHandler("spy_autonomy_check", spy_autonomy_check_command),
        CommandHandler("spy_autonomy_execute", spy_autonomy_execute_command),
    ]
