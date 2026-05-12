from __future__ import annotations

import logging

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


def build_spy_0dte_handlers(app_services: dict, admin_chat_id: int):
    """Dedicated SPY/XSP desk commands kept outside the large legacy handler file."""

    def _service():
        return app_services.get("spy_0dte_service")

    async def spy_health_command(update, context):
        if not await _is_authorized(update, admin_chat_id):
            return
        service = _service()
        await update.message.reply_text(
            "\n".join([
                "SPY/XSP service health:",
                f"configured={service is not None}",
                f"market_client={getattr(service, 'market_client', None) is not None if service else False}",
                f"news_client={getattr(service, 'news_client', None) is not None if service else False}",
                f"econ_client={getattr(service, 'econ_client', None) is not None if service else False}",
                f"tradier_client={getattr(service, 'tradier_client', None) is not None if service else False}",
            ])
        )

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
                f"• SPY Last: {service._price(payload.get('latest'))}",
                f"• VWAP: {service._price(payload.get('vwap'))}",
                f"• Premarket High/Low: {service._price(payload.get('premarket_high'))} / {service._price(payload.get('premarket_low'))}",
                f"• OR Ceiling/Floor: {service._price(payload.get('opening_range_high'))} / {service._price(payload.get('opening_range_low'))}",
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
        CommandHandler("spy_0dte", spy_0dte_command),
        CommandHandler("spy_midday", spy_midday_command),
        CommandHandler("spy_levels", spy_levels_command),
        CommandHandler("spy_gamma", spy_gamma_command),
    ]
