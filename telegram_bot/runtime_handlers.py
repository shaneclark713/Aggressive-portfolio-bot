from __future__ import annotations

import logging
from typing import Any

from telegram.ext import CommandHandler

logger = logging.getLogger("aggressive_portfolio_bot.telegram.runtime_handlers")


async def _is_authorized(update, admin_chat_id: int) -> bool:
    chat_id = update.effective_chat.id if update.effective_chat else None
    if chat_id == admin_chat_id:
        return True
    logger.warning("Unauthorized runtime command from chat_id=%s expected=%s", chat_id, admin_chat_id)
    if update.message:
        await update.message.reply_text("Unauthorized.")
    return False


def _bullet_lines(title: str, payload: dict[str, Any] | None) -> str:
    payload = payload or {}
    lines = [f"<b>{title}</b>", ""]
    if not payload:
        lines.append("No runtime data available.")
        return "\n".join(lines)
    for key, value in payload.items():
        if isinstance(value, list):
            rendered = ", ".join(str(item) for item in value[:20])
            if len(value) > 20:
                rendered += f", ... +{len(value) - 20} more"
            lines.append(f"• {key}: {rendered}")
        elif isinstance(value, dict):
            lines.append(f"• {key}: {len(value)} fields")
        else:
            lines.append(f"• {key}: {value}")
    return "\n".join(lines)


def build_runtime_handlers(app_services: dict, admin_chat_id: int):
    """Small runtime diagnostics command group kept separate from legacy handlers."""

    async def handler_summary_command(update, context):
        if not await _is_authorized(update, admin_chat_id):
            return
        summary = context.application.bot_data.get("handler_summary", {}) if context.application else {}
        await update.message.reply_text(_bullet_lines("Telegram Handler Summary", summary), parse_mode="HTML")

    async def recovery_status_command(update, context):
        if not await _is_authorized(update, admin_chat_id):
            return
        summary = app_services.get("startup_recovery_last_summary") or {}
        await update.message.reply_text(_bullet_lines("Startup Recovery Status", summary), parse_mode="HTML")

    async def risk_status_command(update, context):
        if not await _is_authorized(update, admin_chat_id):
            return
        risk_service = app_services.get("risk_service")
        if risk_service is None or not hasattr(risk_service, "status"):
            await update.message.reply_text("Risk service is not configured.")
            return
        trade_style = context.args[0] if context.args else "day_trade"
        try:
            status = risk_service.status(trade_style=trade_style)
            await update.message.reply_text(_bullet_lines("Risk Status", status), parse_mode="HTML")
        except Exception as exc:
            logger.exception("Risk status command failed: %s", exc)
            await update.message.reply_text(f"Risk status failed: {type(exc).__name__}: {exc}")

    async def execution_guard_status_command(update, context):
        if not await _is_authorized(update, admin_chat_id):
            return
        guard = app_services.get("execution_guard_service")
        live_execution = app_services.get("live_execution_service")
        if guard is None and live_execution is not None:
            guard = getattr(live_execution, "execution_guard_service", None)
        if guard is None or not hasattr(guard, "status"):
            await update.message.reply_text("Execution guard is not configured.")
            return
        await update.message.reply_text(_bullet_lines("Execution Guard Status", guard.status()), parse_mode="HTML")

    async def runtime_status_command(update, context):
        if not await _is_authorized(update, admin_chat_id):
            return
        summary = {
            "market_client": app_services.get("market_client") is not None,
            "news_client": app_services.get("news_client") is not None,
            "econ_client": app_services.get("econ_client") is not None,
            "scanner": app_services.get("scanner") is not None,
            "execution_router": app_services.get("execution_router") is not None,
            "live_execution_service": app_services.get("live_execution_service") is not None,
            "risk_service": app_services.get("risk_service") is not None,
            "position_sync_service": app_services.get("position_sync_service") is not None,
            "startup_recovery_service": app_services.get("startup_recovery_service") is not None,
            "execution_guard_service": app_services.get("execution_guard_service") is not None,
            "spy_0dte_service": app_services.get("spy_0dte_service") is not None,
        }
        await update.message.reply_text(_bullet_lines("Runtime Status", summary), parse_mode="HTML")

    return [
        CommandHandler("handler_summary", handler_summary_command),
        CommandHandler("recovery_status", recovery_status_command),
        CommandHandler("risk_status", risk_status_command),
        CommandHandler("execution_guard_status", execution_guard_status_command),
        CommandHandler("runtime_status", runtime_status_command),
    ]
