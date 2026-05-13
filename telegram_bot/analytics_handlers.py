from __future__ import annotations

import logging

from telegram.ext import CommandHandler

from services.iv_analyzer import IVAnalyzer
from services.options_chain_ingest_service import OptionsChainIngestService
from services.options_chain_service import OptionsChainService
from services.options_flow_analyzer import OptionsFlowAnalyzer
from services.sector_analyzer import SectorAnalyzer
from services.ticker_research_service import TickerResearchService
from telegram_bot.formatters import (
    format_chain_summary,
    format_flow_status,
    format_iv_status,
    format_ml_weights,
    format_sector_status,
    format_ticker_history,
    format_ticker_research_result,
    format_ticker_scan_result,
)

logger = logging.getLogger("aggressive_portfolio_bot.telegram.analytics_handlers")


def _meta_key(name: str) -> str:
    return f"__meta__.ui.{name}"


async def _is_authorized(update, admin_chat_id: int) -> bool:
    chat_id = update.effective_chat.id if update.effective_chat else None
    if chat_id == admin_chat_id:
        return True
    logger.warning("Unauthorized analytics command from chat_id=%s expected=%s", chat_id, admin_chat_id)
    if update.message:
        await update.message.reply_text("Unauthorized.")
    return False


def _settings_payload(settings_repo, name: str, default: dict | None = None) -> dict:
    default = default or {}
    try:
        overrides = settings_repo.get_filter_overrides()
        value = overrides.get(_meta_key(name))
        if isinstance(value, dict):
            return {**default, **value}
        if isinstance(value, str):
            import json
            return {**default, **json.loads(value)}
    except Exception:
        pass
    return dict(default)


def build_analytics_handlers(app_services: dict, config_service, admin_chat_id: int):
    """Analytics command group extracted from the large legacy Telegram handler file."""

    settings_repo = config_service.settings_repo
    sector_analyzer = SectorAnalyzer()
    flow_analyzer = OptionsFlowAnalyzer()
    iv_analyzer = IVAnalyzer()
    chain_service = OptionsChainService()
    options_chain_ingest = app_services.get("options_chain_ingest_service") or OptionsChainIngestService(
        settings_repo,
        app_services.get("tradier_market_data_client") or app_services.get("tradier_live_client") or app_services.get("tradier_client"),
    )
    ticker_research_service = app_services.get("ticker_research_service") or TickerResearchService(
        storage_path=getattr(config_service.settings, "storage_path", "./data"),
        scanner=app_services.get("scanner"),
        market_client=app_services.get("market_client"),
        news_client=app_services.get("news_client"),
        options_chain_ingest=options_chain_ingest,
        chain_service=chain_service,
        iv_analyzer=iv_analyzer,
        flow_analyzer=flow_analyzer,
    )

    def _option_chain_rows() -> list[dict]:
        value = _settings_payload(settings_repo, "last_option_chain", {"rows": []})
        return list(value.get("rows", []))

    def _options_flow_rows() -> list[dict]:
        value = _settings_payload(settings_repo, "options_flow_rows", {"rows": []})
        return list(value.get("rows", []))

    async def ml_weights(update, context):
        if not await _is_authorized(update, admin_chat_id):
            return
        weights = _settings_payload(settings_repo, "ml_weights", {})
        await update.message.reply_text(format_ml_weights(weights), parse_mode="HTML")

    async def sector_status(update, context):
        if not await _is_authorized(update, admin_chat_id):
            return
        discovery = app_services.get("discovery_service")
        rows = await discovery.get_candidate_rows("market", force_refresh=False) if discovery else []
        symbols = [row["symbol"] for row in rows[:25] if isinstance(row, dict) and row.get("symbol")]
        await update.message.reply_text(format_sector_status(sector_analyzer.summarize(symbols)), parse_mode="HTML")

    async def flow_alerts(update, context):
        if not await _is_authorized(update, admin_chat_id):
            return
        await update.message.reply_text(format_flow_status(flow_analyzer.summarize(_options_flow_rows())), parse_mode="HTML")

    async def iv_status(update, context):
        if not await _is_authorized(update, admin_chat_id):
            return
        await update.message.reply_text(format_iv_status(iv_analyzer.summarize_chain(_option_chain_rows())), parse_mode="HTML")

    async def refresh_option_chain(update, context):
        if not await _is_authorized(update, admin_chat_id):
            return
        if len(context.args) < 1:
            await update.message.reply_text("Usage: /refresh_option_chain <symbol> [expiration]")
            return
        symbol = context.args[0].upper()
        expiration = context.args[1] if len(context.args) > 1 else None
        if app_services.get("tradier_client") is None and app_services.get("tradier_live_client") is None:
            await update.message.reply_text("Tradier client not configured.")
            return
        payload = await options_chain_ingest.refresh_chain(symbol, expiration=expiration)
        await update.message.reply_text(
            format_chain_summary(payload["summary"]) + f"\n\n<b>Symbol:</b> {symbol}",
            parse_mode="HTML",
        )

    async def chain_status(update, context):
        if not await _is_authorized(update, admin_chat_id):
            return
        await update.message.reply_text(format_chain_summary(chain_service.summarize_chain(_option_chain_rows())), parse_mode="HTML")

    async def scan_ticker(update, context):
        if not await _is_authorized(update, admin_chat_id):
            return
        scanner = app_services.get("scanner")
        if scanner is None:
            await update.message.reply_text("Scanner service not configured.")
            return
        if not context.args:
            await update.message.reply_text("Usage: /scan_ticker <symbol> [market|premarket|midday|overnight|catalyst]")
            return
        symbol = context.args[0].upper()
        scan_type = context.args[1].lower() if len(context.args) >= 2 else "market"
        payload = await scanner.scan_ticker_overview(symbol, scan_type=scan_type)
        await update.message.reply_text(format_ticker_scan_result(payload), parse_mode="HTML")

    async def research_ticker(update, context):
        if not await _is_authorized(update, admin_chat_id):
            return
        if not context.args:
            await update.message.reply_text("Usage: /research_ticker <symbol> [market|premarket|midday|overnight|catalyst]")
            return
        symbol = context.args[0].upper()
        scan_type = context.args[1].lower() if len(context.args) >= 2 else "market"
        payload = await ticker_research_service.research_ticker(symbol, scan_type=scan_type, include_options=True)
        await update.message.reply_text(format_ticker_research_result(payload), parse_mode="HTML")

    async def ticker_history(update, context):
        if not await _is_authorized(update, admin_chat_id):
            return
        symbol = context.args[0].upper() if context.args else None
        try:
            limit = int(context.args[1]) if len(context.args) >= 2 else 10
        except Exception:
            limit = 10
        rows = ticker_research_service.list_history(symbol=symbol, limit=limit)
        await update.message.reply_text(format_ticker_history(rows, symbol=symbol), parse_mode="HTML")

    return [
        CommandHandler("ml_weights", ml_weights),
        CommandHandler("sector_status", sector_status),
        CommandHandler("flow_alerts", flow_alerts),
        CommandHandler("iv_status", iv_status),
        CommandHandler("refresh_option_chain", refresh_option_chain),
        CommandHandler("chain_status", chain_status),
        CommandHandler("scan_ticker", scan_ticker),
        CommandHandler("research_ticker", research_ticker),
        CommandHandler("ticker_history", ticker_history),
    ]
