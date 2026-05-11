from __future__ import annotations

from telegram.ext import CommandHandler


async def _is_authorized(update, admin_chat_id: int) -> bool:
    if update.effective_chat and update.effective_chat.id == admin_chat_id:
        return True
    if update.message:
        await update.message.reply_text("Unauthorized.")
    return False


def build_spy_0dte_handlers(app_services: dict, admin_chat_id: int):
    """Dedicated SPY/XSP desk commands kept outside the large legacy handler file."""

    async def spy_0dte_command(update, context):
        if not await _is_authorized(update, admin_chat_id):
            return
        service = app_services.get("spy_0dte_service")
        if service is None:
            await update.message.reply_text("SPY/XSP 0DTE service is not configured.")
            return
        payload = await service.analyze()
        await update.message.reply_text(
            service.format_report(payload, "🧭 SPY/XSP 0DTE Direction Desk"),
            parse_mode="HTML",
        )

    async def spy_midday_command(update, context):
        if not await _is_authorized(update, admin_chat_id):
            return
        service = app_services.get("spy_0dte_service")
        if service is None:
            await update.message.reply_text("SPY/XSP 0DTE service is not configured.")
            return
        payload = await service.analyze()
        await update.message.reply_text(
            service.format_report(payload, "☀️ SPY/XSP 0DTE Midday Desk"),
            parse_mode="HTML",
        )

    async def spy_levels_command(update, context):
        if not await _is_authorized(update, admin_chat_id):
            return
        service = app_services.get("spy_0dte_service")
        if service is None:
            await update.message.reply_text("SPY/XSP 0DTE service is not configured.")
            return
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

    return [
        CommandHandler("spy_0dte", spy_0dte_command),
        CommandHandler("spy_midday", spy_midday_command),
        CommandHandler("spy_levels", spy_levels_command),
    ]
