from __future__ import annotations

import logging
from typing import Any

from telegram.ext import CommandHandler

from telegram_bot.ui_helpers import authorize_update

logger = logging.getLogger("aggressive_portfolio_bot.telegram.spy_performance")


def _section(title: str, rows: list[dict[str, Any]], label_key: str, max_rows: int = 6) -> list[str]:
    lines = ["", f"<b>{title}</b>"]
    if not rows:
        lines.append("• No marked outcomes yet.")
        return lines
    for row in rows[:max_rows]:
        label = row.get(label_key, "unknown")
        lines.append(
            "• "
            f"{label} | "
            f"Win {row.get('win_rate', 0.0)}% | "
            f"W/L {row.get('wins', 0)}/{row.get('losses', 0)} | "
            f"Scored {row.get('scored_count', 0)} | "
            f"Avg Conf {row.get('avg_confidence', 0.0)} | "
            f"Avg Struct {row.get('avg_structure_score', 0.0)}"
        )
    return lines


def format_setup_performance(summary: dict[str, Any]) -> str:
    if not summary or summary.get("marked_count", 0) == 0:
        return "<b>SPY/XSP Setup Performance</b>\n\nNo marked scan outcomes yet."
    lines = [
        "<b>SPY/XSP Setup Performance</b>",
        "",
        f"• Lookback Limit: {summary.get('limit', 0)}",
        f"• Marked Scans: {summary.get('marked_count', 0)}",
        f"• Scored Win/Loss: {summary.get('scored_count', 0)}",
        f"• Wins: {summary.get('wins', 0)}",
        f"• Losses: {summary.get('losses', 0)}",
        f"• Overall Win Rate: {summary.get('win_rate', 0.0)}%",
    ]
    lines.extend(_section("By Scan Type", summary.get("by_scan_type", []), "scan_type"))
    lines.extend(_section("By Structure Bias", summary.get("by_structure_bias", []), "structure_bias"))
    lines.extend(_section("By Confidence Grade", summary.get("by_confidence_grade", []), "confidence_grade"))
    lines.extend(_section("By Dealer Regime", summary.get("by_dealer_regime", []), "dealer_regime"))
    return "\n".join(lines)


def build_spy_performance_handlers(app_services: dict, admin_chat_id: int):
    """SPY/XSP setup performance analytics commands for Phase 5.2."""

    def _journal_repo():
        return app_services.get("spy_scan_journal_repo")

    async def spy_setup_stats_command(update, context):
        if not await authorize_update(update, admin_chat_id):
            return
        journal = _journal_repo()
        if journal is None:
            await update.message.reply_text("SPY/XSP scan journal is not configured.")
            return
        if not hasattr(journal, "setup_performance_summary"):
            await update.message.reply_text("SPY/XSP setup performance summary is not available yet.")
            return
        try:
            limit = 250
            if context.args:
                limit = max(25, min(1000, int(context.args[0])))
            summary = journal.setup_performance_summary(limit=limit)
            await update.message.reply_text(format_setup_performance(summary), parse_mode="HTML")
        except Exception as exc:
            logger.exception("SPY/XSP setup performance command failed: %s", exc)
            await update.message.reply_text(f"SPY/XSP setup stats failed: {type(exc).__name__}: {exc}")

    return [
        CommandHandler("spy_setup_stats", spy_setup_stats_command),
        CommandHandler("setup_performance", spy_setup_stats_command),
    ]
