from __future__ import annotations

import logging
from typing import Any

from telegram.ext import CommandHandler

from telegram_bot.ui_helpers import authorize_update

logger = logging.getLogger("aggressive_portfolio_bot.telegram.spy_dashboard")


def _top_bucket(rows: list[dict[str, Any]], label_key: str) -> str:
    if not rows:
        return "n/a"
    row = rows[0]
    return (
        f"{row.get(label_key, 'unknown')} "
        f"({row.get('win_rate', 0.0)}% win, N={row.get('scored_count', 0)})"
    )


def _recent_rows(rows: list[dict[str, Any]], max_rows: int = 5) -> list[str]:
    if not rows:
        return ["• No recent scans saved."]
    lines: list[str] = []
    for row in rows[:max_rows]:
        lines.append(
            "• "
            f"#{row.get('scan_id')} {row.get('scan_type', 'scan')} | "
            f"{row.get('structure_bias', 'n/a')} | "
            f"Conf {row.get('confidence_grade', 'n/a')} {row.get('confidence_score', 'n/a')} | "
            f"Outcome {row.get('outcome') or 'unmarked'}"
        )
    return lines


def format_spy_dashboard(report: dict[str, Any]) -> str:
    score = report.get("score", {}) or {}
    aplus = report.get("a_plus", {}) or {}
    accuracy = report.get("accuracy", {}) or {}
    perf = report.get("performance", {}) or {}
    calibration = report.get("calibration", {}) or {}
    recent = report.get("recent", {}) or {}

    lines = [
        "<b>SPY/XSP Intelligence Dashboard</b>",
        "",
        "<b>Current Setup</b>",
        f"• Score: {score.get('score', 0)} / 100",
        f"• Grade: {score.get('grade', 'n/a')}",
        f"• Action: {score.get('action', 'n/a')}",
        f"• A+ Gate: {aplus.get('label', 'n/a')}",
        f"• Dealer Regime: {score.get('dealer_regime', 'unknown')}",
        f"• Confidence: {score.get('confidence_score', 0)}",
        f"• Structure: {score.get('structure_score', 0)}",
        "",
        "<b>Historical Edge</b>",
        f"• Recent Win Rate: {accuracy.get('win_rate', 0.0)}%",
        f"• Wins/Losses: {accuracy.get('wins', 0)}/{accuracy.get('losses', 0)}",
        f"• Avg Win Confidence: {accuracy.get('avg_win_confidence', 0.0)}",
        f"• Avg Loss Confidence: {accuracy.get('avg_loss_confidence', 0.0)}",
        f"• Top Structure: {_top_bucket(perf.get('by_structure_bias', []), 'structure_bias')}",
        f"• Top Confidence Grade: {_top_bucket(perf.get('by_confidence_grade', []), 'confidence_grade')}",
        f"• Top Dealer Regime: {_top_bucket(perf.get('by_dealer_regime', []), 'dealer_regime')}",
        "",
        "<b>Calibration</b>",
        f"• Avg Confidence: {calibration.get('avg_confidence', 0.0)}",
        f"• Actual Win Rate: {calibration.get('overall_win_rate', 0.0)}%",
        f"• Confidence Gap: {calibration.get('overall_gap', 0.0)} pts",
    ]
    blockers = aplus.get("blockers", []) or []
    confirmations = aplus.get("confirmations", []) or []
    triggers = aplus.get("required_price_triggers", []) or []
    if blockers:
        lines.extend(["", "<b>A+ Blockers</b>"])
        lines.extend(f"• {item}" for item in blockers[:6])
    if confirmations:
        lines.extend(["", "<b>A+ Confirmations</b>"])
        lines.extend(f"• {item}" for item in confirmations[:6])
    if triggers:
        lines.extend(["", "<b>Required Price Triggers</b>"])
        lines.extend(f"• {item}" for item in triggers[:6])
    lines.extend(["", "<b>Recent Scans</b>"])
    lines.extend(_recent_rows(recent.get("rows", []) or []))
    return "\n".join(lines)


def build_spy_dashboard_handlers(app_services: dict, admin_chat_id: int):
    """SPY/XSP dashboard/report analytics commands for Phase 5.5."""

    def _service():
        return app_services.get("spy_0dte_service")

    def _journal_repo():
        return app_services.get("spy_scan_journal_repo")

    def _scorer():
        return app_services.get("spy_setup_score_service")

    async def spy_dashboard_command(update, context):
        if not await authorize_update(update, admin_chat_id):
            return
        service = _service()
        journal = _journal_repo()
        scorer = _scorer()
        if service is None:
            await update.message.reply_text("SPY/XSP 0DTE service is not configured.")
            return
        if journal is None:
            await update.message.reply_text("SPY/XSP scan journal is not configured.")
            return
        if scorer is None:
            await update.message.reply_text("SPY/XSP setup scorer is not configured.")
            return
        try:
            await update.message.reply_text("Building SPY/XSP intelligence dashboard...")
            payload = await service.analyze()
            score = scorer.score_payload(payload)
            aplus = scorer.a_plus_filter(payload) if hasattr(scorer, "a_plus_filter") else {}
            report = {
                "score": score,
                "a_plus": aplus,
                "accuracy": journal.accuracy_summary(limit=250),
                "performance": journal.setup_performance_summary(limit=250) if hasattr(journal, "setup_performance_summary") else {},
                "calibration": journal.confidence_calibration_summary(limit=500) if hasattr(journal, "confidence_calibration_summary") else {},
                "recent": journal.summarize_recent(limit=5),
            }
            await update.message.reply_text(format_spy_dashboard(report), parse_mode="HTML")
        except Exception as exc:
            logger.exception("SPY/XSP dashboard command failed: %s", exc)
            await update.message.reply_text(f"SPY/XSP dashboard failed: {type(exc).__name__}: {exc}")

    return [
        CommandHandler("spy_dashboard", spy_dashboard_command),
        CommandHandler("spy_report", spy_dashboard_command),
    ]
