from __future__ import annotations

import logging
from typing import Any

from telegram.ext import CommandHandler

from telegram_bot.ui_helpers import authorize_update

logger = logging.getLogger("aggressive_portfolio_bot.telegram.spy_calibration")


def _format_scan_list(title: str, rows: list[dict[str, Any]]) -> list[str]:
    lines = ["", f"<b>{title}</b>"]
    if not rows:
        lines.append("• None in current lookback.")
        return lines
    for row in rows[:8]:
        lines.append(
            "• "
            f"#{row.get('scan_id')} "
            f"{row.get('scan_type', 'scan')} | "
            f"Conf {row.get('confidence_grade', 'n/a')} {row.get('confidence_score', 'n/a')} | "
            f"{row.get('structure_bias', 'n/a')} | "
            f"{row.get('dealer_regime', 'n/a')} | "
            f"Outcome {row.get('outcome', 'n/a')}"
        )
    return lines


def format_confidence_calibration(summary: dict[str, Any]) -> str:
    if not summary or summary.get("scored_count", 0) == 0:
        return "<b>SPY/XSP Confidence Calibration</b>\n\nNo scored win/loss outcomes yet."
    lines = [
        "<b>SPY/XSP Confidence Calibration</b>",
        "",
        f"• Lookback Limit: {summary.get('limit', 0)}",
        f"• Marked Scans: {summary.get('marked_count', 0)}",
        f"• Scored Win/Loss: {summary.get('scored_count', 0)}",
        f"• Avg Confidence: {summary.get('avg_confidence', 0.0)}",
        f"• Actual Win Rate: {summary.get('overall_win_rate', 0.0)}%",
        f"• Overall Gap: {summary.get('overall_gap', 0.0)} pts",
        "",
        "<b>Calibration Buckets</b>",
    ]
    for row in summary.get("buckets", []) or []:
        lines.append(
            "• "
            f"{row.get('bucket')} ({row.get('range_low')}-{row.get('range_high')}) | "
            f"Win {row.get('actual_win_rate', 0.0)}% | "
            f"Avg Conf {row.get('avg_confidence', 0.0)} | "
            f"Gap {row.get('calibration_gap', 0.0)} | "
            f"N={row.get('scored_count', 0)} | "
            f"{row.get('status', 'n/a')}"
        )
    lines.extend(_format_scan_list("High-Confidence Losses", summary.get("high_confidence_losses", []) or []))
    lines.extend(_format_scan_list("Low-Confidence Winners", summary.get("low_confidence_wins", []) or []))
    return "\n".join(lines)


def build_spy_calibration_handlers(app_services: dict, admin_chat_id: int):
    """SPY/XSP confidence calibration commands for Phase 5.3."""

    def _journal_repo():
        return app_services.get("spy_scan_journal_repo")

    async def spy_calibration_command(update, context):
        if not await authorize_update(update, admin_chat_id):
            return
        journal = _journal_repo()
        if journal is None:
            await update.message.reply_text("SPY/XSP scan journal is not configured.")
            return
        if not hasattr(journal, "confidence_calibration_summary"):
            await update.message.reply_text("SPY/XSP confidence calibration is not available yet.")
            return
        try:
            limit = 500
            if context.args:
                limit = max(25, min(1000, int(context.args[0])))
            summary = journal.confidence_calibration_summary(limit=limit)
            await update.message.reply_text(format_confidence_calibration(summary), parse_mode="HTML")
        except Exception as exc:
            logger.exception("SPY/XSP confidence calibration command failed: %s", exc)
            await update.message.reply_text(f"SPY/XSP calibration failed: {type(exc).__name__}: {exc}")

    return [
        CommandHandler("spy_calibration", spy_calibration_command),
        CommandHandler("confidence_calibration", spy_calibration_command),
    ]
