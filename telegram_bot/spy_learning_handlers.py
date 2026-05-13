from __future__ import annotations

import logging
from typing import Any

from services.spy_learning_service import SpyLearningService
from telegram.ext import CommandHandler

from telegram_bot.ui_helpers import authorize_update

logger = logging.getLogger("aggressive_portfolio_bot.telegram.spy_learning")


def format_learning_summary(summary: dict[str, Any]) -> str:
    if not summary.get("available", False):
        warnings = summary.get("warnings") or [summary.get("reason", "Learning summary unavailable.")]
        return "<b>SPY/XSP Adaptive Learning</b>\n\n" + "\n".join(f"• {item}" for item in warnings)

    lines = [
        "<b>SPY/XSP Adaptive Learning</b>",
        "",
        "<i>Advisory only. No auto-trading or automatic weight mutation.</i>",
        "",
        f"• Lookback Limit: {summary.get('lookback_limit', 0)}",
        f"• Scored Outcomes: {summary.get('scored_count', 0)}",
        f"• Overall Win Rate: {summary.get('overall_win_rate', 0.0)}%",
    ]

    warnings = summary.get("warnings", []) or []
    if warnings:
        lines.extend(["", "<b>Warnings</b>"])
        lines.extend(f"• {item}" for item in warnings[:5])

    recommendations = summary.get("recommendations", []) or []
    if not recommendations:
        lines.extend(["", "<b>Recommendations</b>", "• Not enough actionable edge yet. Keep marking outcomes."])
        return "\n".join(lines)

    lines.extend(["", "<b>Learning Recommendations</b>"])
    for row in recommendations[:10]:
        lines.append(
            "• "
            f"[{row.get('type', 'note')}] "
            f"{row.get('recommendation', 'n/a')} "
            f"(N={row.get('sample_size', 0)})"
        )
    return "\n".join(lines)


def build_spy_learning_handlers(app_services: dict, admin_chat_id: int):
    """Adaptive learning report commands for Phase 5.6."""

    def _learning_service():
        return app_services.get("spy_learning_service") or SpyLearningService(app_services.get("spy_scan_journal_repo"))

    async def spy_learning_command(update, context):
        if not await authorize_update(update, admin_chat_id):
            return
        service = _learning_service()
        try:
            limit = 500
            if context.args:
                limit = max(25, min(1000, int(context.args[0])))
            summary = service.summarize_learning(limit=limit)
            await update.message.reply_text(format_learning_summary(summary), parse_mode="HTML")
        except Exception as exc:
            logger.exception("SPY/XSP learning command failed: %s", exc)
            await update.message.reply_text(f"SPY/XSP learning failed: {type(exc).__name__}: {exc}")

    return [
        CommandHandler("spy_learning", spy_learning_command),
        CommandHandler("learning_loop", spy_learning_command),
    ]
