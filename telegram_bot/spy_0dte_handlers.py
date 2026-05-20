from __future__ import annotations

import logging
from statistics import median

from telegram.ext import CommandHandler

logger = logging.getLogger("aggressive_portfolio_bot.telegram.spy_0dte")


async def _is_authorized(update, admin_chat_id: int) -> bool:
    chat_id = update.effective_chat.id if update.effective_chat else None
    if chat_id == admin_chat_id:
        return True
    logger.warning("Unauthorized SPY/XSP command from chat_id=%s expected=%s", chat_id, admin_chat_id)
    if update.message:
        await update.message.reply_text("Unauthorized.")
    return False


async def _run_report(update, service, title: str) -> None:
    try:
        await update.message.reply_text("Running SPY/XSP desk scan...")
        payload = await service.analyze()
        await update.message.reply_text(service.format_report(payload, title), parse_mode="HTML")
    except Exception as exc:
        logger.exception("SPY/XSP command failed: %s", exc)
        await update.message.reply_text(f"SPY/XSP scan failed: {type(exc).__name__}: {exc}")


def _estimate_underlying_from_chain(rows: list[dict]) -> float:
    strikes = []
    weighted = []
    for row in rows or []:
        try:
            strike = float(row.get("strike") or 0)
        except Exception:
            strike = 0.0
        if strike <= 0:
            continue
        volume = float(row.get("volume") or 0)
        open_interest = float(row.get("open_interest") or row.get("openInterest") or 0)
        weight = max(1, int(min(50, volume + (open_interest * 0.05))))
        strikes.append(strike)
        weighted.extend([strike] * weight)
    if weighted:
        return float(median(weighted))
    if strikes:
        return float(median(strikes))
    return 0.0

def _fmt_price(value) -> str:
    try:
        if value is None:
            return "n/a"
        return f"{float(value):.2f}"
    except Exception:
        return "n/a"



def _format_scan_history(summary: dict) -> str:
    rows = summary.get("rows", []) or []
    if not rows:
        return "<b>SPY/XSP Scan History</b>\n\nNo saved scans yet."
    lines = [
        "<b>SPY/XSP Scan History</b>",
        "",
        f"• Saved Scans Shown: {summary.get('count', len(rows))}",
        f"• Avg Confidence: {summary.get('avg_confidence', 0.0)}",
        f"• Avg Trend Probability: {summary.get('avg_trend_probability', 0.0)}%",
        "",
        "<b>Recent Scans</b>",
    ]
    for row in rows[:10]:
        outcome = row.get("outcome") or "unmarked"
        lines.append(
            "• "
            f"#{row.get('scan_id')} "
            f"{row.get('scan_type', 'scan')} | "
            f"{row.get('created_at', '')} | "
            f"{row.get('structure_bias', 'n/a')} | "
            f"Conf {row.get('confidence_grade', 'n/a')} {row.get('confidence_score', 'n/a')} | "
            f"Trend {row.get('trend_probability', 'n/a')}% | "
            f"Dealer {row.get('dealer_regime', 'n/a')} | "
            f"Outcome {outcome}"
        )
    return "\n".join(lines)


def _format_accuracy(summary: dict) -> str:
    lines = [
        "<b>SPY/XSP Accuracy Summary</b>",
        "",
        f"• Marked Scans: {summary.get('marked_count', 0)}",
        f"• Scored Win/Loss: {summary.get('scored_count', 0)}",
        f"• Wins: {summary.get('wins', 0)}",
        f"• Losses: {summary.get('losses', 0)}",
        f"• Win Rate: {summary.get('win_rate', 0.0)}%",
        f"• Avg Win Confidence: {summary.get('avg_win_confidence', 0.0)}",
        f"• Avg Loss Confidence: {summary.get('avg_loss_confidence', 0.0)}",
    ]
    rows = summary.get("rows", []) or []
    if rows:
        lines.extend(["", "<b>Recent Marked Scans</b>"])
        for row in rows[:8]:
            lines.append(
                "• "
                f"#{row.get('scan_id')} {row.get('outcome')} | "
                f"Conf {row.get('confidence_grade', 'n/a')} {row.get('confidence_score', 'n/a')} | "
                f"{row.get('dealer_regime', 'n/a')}"
            )
    return "\n".join(lines)


def _format_regimes(rows: list[dict]) -> str:
    if not rows:
        return "<b>SPY/XSP Best Regimes</b>\n\nNo marked scan outcomes yet."
    lines = ["<b>SPY/XSP Best Regimes</b>", ""]
    for row in rows[:10]:
        lines.append(
            "• "
            f"{row.get('dealer_regime', 'unknown')} | "
            f"Win {row.get('win_rate', 0.0)}% | "
            f"Wins {row.get('wins', 0)} | "
            f"Scored {row.get('scored_count', 0)} | "
            f"Avg Conf {row.get('avg_confidence', 0.0)}"
        )
    return "\n".join(lines)


def _format_setup_score(score: dict) -> str:
    lines = [
        "<b>SPY/XSP Setup Score</b>",
        "",
        f"• Grade: {score.get('grade', 'n/a')}",
        f"• Score: {score.get('score', 0)} / 100",
        f"• Action: {score.get('action', 'n/a')}",
        f"• Dealer Regime: {score.get('dealer_regime', 'unknown')}",
        f"• Confidence: {score.get('confidence_score', 0)}",
        f"• Structure Strength: {score.get('structure_score', 0)}",
        f"• Trend Probability: {score.get('trend_probability', 0)}%",
        f"• Mean-Reversion Probability: {score.get('mean_reversion_probability', 0)}%",
    ]
    reasons = score.get("reasons", []) or []
    warnings = score.get("warnings", []) or []
    if reasons:
        lines.extend(["", "<b>Positive Factors</b>"])
        lines.extend(f"• {item}" for item in reasons[:6])
    if warnings:
        lines.extend(["", "<b>Warnings</b>"])
        lines.extend(f"• {item}" for item in warnings[:6])
    return "\n".join(lines)


def build_spy_0dte_handlers(app_services: dict, admin_chat_id: int):
    """Dedicated SPY/XSP desk commands kept outside the large legacy handler file."""

    def _service():
        return app_services.get("spy_0dte_service")

    def _journal_repo():
        return app_services.get("spy_scan_journal_repo")

    def _setup_scorer():
        return app_services.get("spy_setup_score_service")

    async def spy_health_command(update, context):
        if not await _is_authorized(update, admin_chat_id):
            return
        service = _service()
        journal = _journal_repo()
        scorer = _setup_scorer()
        await update.message.reply_text(
            "\n".join([
                "SPY/XSP service health:",
                f"configured={service is not None}",
                f"journal_repo={journal is not None}",
                f"setup_scorer={scorer is not None}",
                f"market_client={getattr(service, 'market_client', None) is not None if service else False}",
                f"news_client={getattr(service, 'news_client', None) is not None if service else False}",
                f"econ_client={getattr(service, 'econ_client', None) is not None if service else False}",
                f"tradier_client={getattr(service, 'tradier_client', None) is not None if service else False}",
            ])
        )

    async def spy_setup_score_command(update, context):
        if not await _is_authorized(update, admin_chat_id):
            return
        service = _service()
        scorer = _setup_scorer()
        if service is None or scorer is None:
            await update.message.reply_text("SPY/XSP setup scoring is not configured.")
            return
        try:
            await update.message.reply_text("Scoring current SPY/XSP setup...")
            payload = await service.analyze()
            score = scorer.score_payload(payload)
            await update.message.reply_text(_format_setup_score(score), parse_mode="HTML")
        except Exception as exc:
            logger.exception("SPY/XSP setup score command failed: %s", exc)
            await update.message.reply_text(f"SPY/XSP setup score failed: {type(exc).__name__}: {exc}")

    async def spy_history_command(update, context):
        if not await _is_authorized(update, admin_chat_id):
            return
        journal = _journal_repo()
        if journal is None:
            await update.message.reply_text("SPY/XSP scan journal is not configured.")
            return
        try:
            limit = 10
            if context.args:
                limit = max(1, min(25, int(context.args[0])))
            summary = journal.summarize_recent(limit=limit)
            await update.message.reply_text(_format_scan_history(summary), parse_mode="HTML")
        except Exception as exc:
            logger.exception("SPY/XSP history command failed: %s", exc)
            await update.message.reply_text(f"SPY/XSP history failed: {type(exc).__name__}: {exc}")

    async def spy_mark_win_command(update, context):
        await _mark_outcome(update, context, "win")

    async def spy_mark_loss_command(update, context):
        await _mark_outcome(update, context, "loss")

    async def spy_mark_neutral_command(update, context):
        await _mark_outcome(update, context, "neutral")

    async def _mark_outcome(update, context, outcome: str):
        if not await _is_authorized(update, admin_chat_id):
            return
        journal = _journal_repo()
        if journal is None:
            await update.message.reply_text("SPY/XSP scan journal is not configured.")
            return
        if not context.args:
            await update.message.reply_text(f"Usage: /spy_mark_{outcome} <scan_id> [notes]")
            return
        try:
            scan_id = int(context.args[0])
            notes = " ".join(context.args[1:]).strip() if len(context.args) > 1 else ""
            row = journal.mark_outcome(scan_id, outcome, notes=notes)
            if not row:
                await update.message.reply_text(f"No scan found for scan_id={scan_id}.")
                return
            await update.message.reply_text(
                "\n".join([
                    "<b>SPY/XSP Outcome Marked</b>",
                    "",
                    f"• Scan: #{row.get('scan_id')}",
                    f"• Outcome: {row.get('outcome')}",
                    f"• Bias: {row.get('structure_bias', 'n/a')}",
                    f"• Confidence: {row.get('confidence_grade', 'n/a')} {row.get('confidence_score', 'n/a')}",
                    f"• Dealer Regime: {row.get('dealer_regime', 'n/a')}",
                    f"• Notes: {row.get('outcome_notes') or 'none'}",
                ]),
                parse_mode="HTML",
            )
        except Exception as exc:
            logger.exception("SPY/XSP mark outcome failed: %s", exc)
            await update.message.reply_text(f"SPY/XSP outcome mark failed: {type(exc).__name__}: {exc}")

    async def spy_accuracy_command(update, context):
        if not await _is_authorized(update, admin_chat_id):
            return
        journal = _journal_repo()
        if journal is None:
            await update.message.reply_text("SPY/XSP scan journal is not configured.")
            return
        try:
            limit = 100
            if context.args:
                limit = max(10, min(500, int(context.args[0])))
            summary = journal.accuracy_summary(limit=limit)
            await update.message.reply_text(_format_accuracy(summary), parse_mode="HTML")
        except Exception as exc:
            logger.exception("SPY/XSP accuracy command failed: %s", exc)
            await update.message.reply_text(f"SPY/XSP accuracy failed: {type(exc).__name__}: {exc}")

    async def best_regimes_command(update, context):
        if not await _is_authorized(update, admin_chat_id):
            return
        journal = _journal_repo()
        if journal is None:
            await update.message.reply_text("SPY/XSP scan journal is not configured.")
            return
        try:
            limit = 250
            if context.args:
                limit = max(25, min(1000, int(context.args[0])))
            rows = journal.regime_summary(limit=limit)
            await update.message.reply_text(_format_regimes(rows), parse_mode="HTML")
        except Exception as exc:
            logger.exception("SPY/XSP best regimes command failed: %s", exc)
            await update.message.reply_text(f"SPY/XSP best regimes failed: {type(exc).__name__}: {exc}")

    async def spy_chain_gamma_command(update, context):
        if not await _is_authorized(update, admin_chat_id):
            return
        service = _service()
        if service is None:
            await update.message.reply_text("SPY/XSP 0DTE service is not configured.")
            return
        try:
            await update.message.reply_text("Loading Tradier-only SPY option-chain gamma...")
            rows = await service._safe_chain_rows("SPY")
            latest = _estimate_underlying_from_chain(rows)
            dealer = service.dealer_gamma.summarize(latest, rows).as_dict()
            lines = [
                "<b>SPY Tradier-Only Chain Gamma</b>",
                "",
                "<i>Polygon intraday bars are not used for this command.</i>",
                f"• Estimated Underlying Area: {_fmt_price(latest)}",
                f"• Dealer Regime: {dealer.get('dealer_regime', 'unknown')}",
                f"• Exposure Score: {dealer.get('exposure_score', 0)}",
                f"• Pin: {dealer.get('pin', 'n/a')}",
                f"• Flip: {dealer.get('flip', 'n/a')}",
                f"• Support: {dealer.get('support', 'n/a')}",
                f"• Resistance: {dealer.get('resistance', 'n/a')}",
                f"• Contracts Sampled: {len(rows)}",
                "",
                "<b>Dealer Notes</b>",
            ]
            notes = dealer.get("notes", []) or ["Tradier option-chain data unavailable or not enough chain data loaded."]
            lines.extend(f"• {item}" for item in notes[:4])
            await update.message.reply_text("\n".join(lines), parse_mode="HTML")
        except Exception as exc:
            logger.exception("SPY/XSP chain gamma command failed: %s", exc)
            await update.message.reply_text(f"SPY chain gamma failed: {type(exc).__name__}: {exc}")

    async def spy_0dte_command(update, context):
        if not await _is_authorized(update, admin_chat_id):
            return
        service = _service()
        if service is None:
            await update.message.reply_text("SPY/XSP 0DTE service is not configured.")
            return
        await _run_report(update, service, "🧭 SPY/XSP 0DTE Direction Desk")

    async def spy_midday_command(update, context):
        if not await _is_authorized(update, admin_chat_id):
            return
        service = _service()
        if service is None:
            await update.message.reply_text("SPY/XSP 0DTE service is not configured.")
            return
        await _run_report(update, service, "☀️ SPY/XSP 0DTE Midday Desk")

    async def spy_levels_command(update, context):
        if not await _is_authorized(update, admin_chat_id):
            return
        service = _service()
        if service is None:
            await update.message.reply_text("SPY/XSP 0DTE service is not configured.")
            return
        try:
            await update.message.reply_text("Loading SPY/XSP levels...")
            payload = await service.analyze()
            zones = payload.get("zones", {})
            structure = payload.get("structure", {})
            confidence = payload.get("confidence", {})
            text = "\n".join([
                "<b>SPY/XSP Key Levels</b>",
                "",
                f"• SPY Last: {_fmt_price(payload.get('latest'))}",
                f"• VWAP: {_fmt_price(payload.get('vwap'))}",
                f"• Premarket High/Low: {_fmt_price(payload.get('premarket_high'))} / {_fmt_price(payload.get('premarket_low'))}",
                f"• OR Ceiling/Floor: {_fmt_price(payload.get('opening_range_high'))} / {_fmt_price(payload.get('opening_range_low'))}",
                f"• Pin/Flip: {zones.get('pin', 'n/a')} / {zones.get('flip', 'n/a')}",
                f"• Support/Resistance: {zones.get('support', 'n/a')} / {zones.get('resistance', 'n/a')}",
                "",
                f"• Structure: {structure.get('bias', 'balanced / tactical')} ({structure.get('score', 0)})",
                f"• Confidence: {confidence.get('grade', 'n/a')} ({confidence.get('score', 0)}/100)",
            ])
            await update.message.reply_text(text, parse_mode="HTML")
        except Exception as exc:
            logger.exception("SPY/XSP levels command failed: %s", exc)
            await update.message.reply_text(f"SPY/XSP levels failed: {type(exc).__name__}: {exc}")

    async def spy_gamma_command(update, context):
        if not await _is_authorized(update, admin_chat_id):
            return
        service = _service()
        if service is None:
            await update.message.reply_text("SPY/XSP 0DTE service is not configured.")
            return
        try:
            await update.message.reply_text("Loading SPY/XSP dealer gamma...")
            payload = await service.analyze()
            dealer = payload.get("dealer_gamma", {})
            zones = payload.get("zones", {})
            lines = [
                "<b>SPY/XSP Dealer Gamma Read</b>",
                "",
                f"• Dealer Regime: {dealer.get('dealer_regime', 'unknown')}",
                f"• Exposure Score: {dealer.get('exposure_score', 0)}",
                f"• Pin: {zones.get('pin', 'n/a')}",
                f"• Flip: {zones.get('flip', 'n/a')}",
                f"• Support: {zones.get('support', 'n/a')}",
                f"• Resistance: {zones.get('resistance', 'n/a')}",
                f"• Contracts Sampled: {payload.get('chain_contracts', 0)}",
                "",
                "<b>Dealer Notes</b>",
            ]
            notes = dealer.get("notes", []) or ["Dealer gamma data unavailable or not enough chain data loaded."]
            lines.extend(f"• {item}" for item in notes[:4])
            await update.message.reply_text("\n".join(lines), parse_mode="HTML")
        except Exception as exc:
            logger.exception("SPY/XSP gamma command failed: %s", exc)
            await update.message.reply_text(f"SPY/XSP gamma failed: {type(exc).__name__}: {exc}")

    return [
        CommandHandler("spy_health", spy_health_command),
        CommandHandler("spy_setup_score", spy_setup_score_command),
        CommandHandler("spy_history", spy_history_command),
        CommandHandler("spy_mark_win", spy_mark_win_command),
        CommandHandler("spy_mark_loss", spy_mark_loss_command),
        CommandHandler("spy_mark_neutral", spy_mark_neutral_command),
        CommandHandler("spy_accuracy", spy_accuracy_command),
        CommandHandler("best_regimes", best_regimes_command),
        CommandHandler("spy_chain_gamma", spy_chain_gamma_command),
        CommandHandler("spy_0dte", spy_0dte_command),
        CommandHandler("spy_midday", spy_midday_command),
        CommandHandler("spy_levels", spy_levels_command),
        CommandHandler("spy_gamma", spy_gamma_command),
      ]
