from __future__ import annotations

import json

from telegram.ext import CallbackQueryHandler, CommandHandler, MessageHandler, filters

from execution.strategy_execution_profiles import StrategyExecutionProfiles
from services.broker_ladder_service import BrokerLadderService
from services.iv_analyzer import IVAnalyzer
from services.options_chain_ingest_service import OptionsChainIngestService
from services.options_chain_service import OptionsChainService
from services.options_flow_analyzer import OptionsFlowAnalyzer
from services.position_sync_service import PositionSyncService
from services.sector_analyzer import SectorAnalyzer
from services.trailing_stop_service import TrailingStopService

from .callbacks import handle_trade_callback
from .keyboards import (
    build_control_panel_keyboard,
    build_execution_menu_keyboard,
    build_execution_profile_edit_keyboard,
    build_execution_profile_menu_keyboard,
    build_ml_menu_keyboard,
    build_options_menu_keyboard,
)
from .formatters import (
    format_chain_summary,
    format_execution_settings,
    format_flow_status,
    format_iv_status,
    format_ladder_execution_result,
    format_ladder_submission,
    format_ml_weights,
    format_open_trails,
    format_options_settings,
    format_position_sync_result,
    format_profile_execution_status,
    format_sector_status,
)


def _meta_key(name: str) -> str:
    return f"__meta__.ui.{name}"


def _parse_meta_value(raw):
    if raw is None:
        return {}
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except Exception:
            return {}
    return {}


async def start_command(update, context):
    await update.message.reply_text("Bot online.")


async def panel_command(update, context):
    await update.message.reply_text("Control Panel", reply_markup=build_control_panel_keyboard())


async def cancel_command(update, context):
    context.user_data.pop("pending_exec_profile_edit", None)
    await update.message.reply_text("Canceled.")


def build_handlers(app_services, config_service, admin_chat_id: int):
    settings_repo = config_service.settings_repo
    sector_analyzer = SectorAnalyzer()
    flow_analyzer = OptionsFlowAnalyzer()
    iv_analyzer = IVAnalyzer()
    chain_service = OptionsChainService()
    profile_store = StrategyExecutionProfiles(settings_repo)
    trailing_stop_service = TrailingStopService(settings_repo)
    options_chain_ingest = OptionsChainIngestService(settings_repo, app_services.get("tradier_client"))
    live_execution_service = app_services.get("live_execution_service")
    broker_ladder_service = BrokerLadderService(app_services.get("execution_router"))
    position_sync_service = PositionSyncService(trailing_stop_service, alpaca_client=app_services.get("alpaca_client"), tradier_client=app_services.get("tradier_client"))

    def _get_ui_settings(name: str, default: dict) -> dict:
        overrides = settings_repo.get_filter_overrides()
        value = overrides.get(_meta_key(name))
        parsed = _parse_meta_value(value)
        merged = dict(default)
        merged.update(parsed)
        return merged

    def _set_ui_settings(name: str, payload: dict) -> dict:
        settings_repo.set_filter_override(_meta_key(name), json.dumps(payload))
        return payload

    def _get_execution_settings() -> dict:
        return _get_ui_settings("execution_settings", {"risk_pct": 0.75, "atr_multiplier": 1.0, "position_mode": "auto", "max_spread_pct": 0.03, "min_volume": 500000, "max_slippage_pct": 0.02, "ladder_steps": 3, "ladder_spacing_pct": 0.01, "trail_type": "percent", "trail_value": 0.02})

    def _get_options_settings() -> dict:
        return _get_ui_settings("options_settings", {"enabled": False, "delta_min": 0.30, "delta_max": 0.70, "min_open_interest": 1000, "expiry_preference": "weekly", "chain_symbol": "SPY"})

    def _update_options_settings(**updates) -> dict:
        current = _get_options_settings()
        current.update(updates)
        return _set_ui_settings("options_settings", current)

    def _get_ml_weights() -> dict:
        return _get_ui_settings("ml_weights", {})

    def _get_option_chain_rows() -> list[dict]:
        value = _get_ui_settings("last_option_chain", {"rows": []})
        return list(value.get("rows", []))

    def _get_options_flow_rows() -> list[dict]:
        value = _get_ui_settings("options_flow_rows", {"rows": []})
        return list(value.get("rows", []))

    async def _authorize_update(update) -> bool:
        if update.effective_chat.id != admin_chat_id:
            target = update.message or getattr(update, "callback_query", None)
            if target is not None:
                if hasattr(target, "reply_text"):
                    await target.reply_text("Unauthorized.")
                elif hasattr(target, "answer"):
                    await target.answer("Unauthorized", show_alert=True)
            return False
        return True

    async def _ml_weights(update, context):
        if await _authorize_update(update):
            await update.message.reply_text(format_ml_weights(_get_ml_weights()), parse_mode="HTML")

    async def _sector_status(update, context):
        if not await _authorize_update(update):
            return
        discovery = app_services.get("discovery_service")
        rows = await discovery.get_candidate_rows("market", force_refresh=False)
        symbols = [row["symbol"] for row in rows[:25]]
        await update.message.reply_text(format_sector_status(sector_analyzer.summarize(symbols)), parse_mode="HTML")

    async def _flow_alerts(update, context):
        if await _authorize_update(update):
            await update.message.reply_text(format_flow_status(flow_analyzer.summarize(_get_options_flow_rows())), parse_mode="HTML")

    async def _iv_status(update, context):
        if await _authorize_update(update):
            await update.message.reply_text(format_iv_status(iv_analyzer.summarize_chain(_get_option_chain_rows())), parse_mode="HTML")

    async def _refresh_option_chain(update, context):
        if not await _authorize_update(update):
            return
        if len(context.args) < 1:
            await update.message.reply_text("Usage: /refresh_option_chain <symbol> [expiration]")
            return
        symbol = context.args[0].upper()
        expiration = context.args[1] if len(context.args) > 1 else None
        if app_services.get("tradier_client") is None:
            await update.message.reply_text("Tradier client not configured.")
            return
        payload = await options_chain_ingest.refresh_chain(symbol, expiration=expiration)
        _update_options_settings(chain_symbol=symbol)
        await update.message.reply_text(format_chain_summary(payload["summary"]) + f"\n\n<b>Symbol:</b> {symbol}", parse_mode="HTML")

    async def _chain_status(update, context):
        if await _authorize_update(update):
            await update.message.reply_text(format_chain_summary(chain_service.summarize_chain(_get_option_chain_rows())), parse_mode="HTML")

    async def _trail_status(update, context):
        if await _authorize_update(update):
            await update.message.reply_text(format_open_trails(trailing_stop_service.list_positions()), parse_mode="HTML")

    async def _sync_positions(update, context):
        if not await _authorize_update(update):
            return
        rows = await position_sync_service.sync_demo_positions()
        await update.message.reply_text(format_position_sync_result(rows), parse_mode="HTML")

    async def _profile_exec_status(update, context):
        if not await _authorize_update(update):
            return
        mode = context.args[0] if len(context.args) >= 1 else config_service.get_execution_mode()
        strategy = context.args[1] if len(context.args) >= 2 else "breakout_box"
        profile = profile_store.get_profile(mode, strategy)
        await update.message.reply_text(format_profile_execution_status(mode, strategy, profile), parse_mode="HTML")

    async def _submit_ladder(update, context):
        if not await _authorize_update(update):
            return
        if len(context.args) < 5:
            await update.message.reply_text("Usage: /submit_ladder <symbol> <side> <total_size> <entry_price> <strategy> [mode]")
            return
        symbol, side, total_size, entry_price, strategy = context.args[:5]
        mode = context.args[5] if len(context.args) >= 6 else config_service.get_execution_mode()
        plan = await live_execution_service.submit_stock_ladder(symbol.upper(), side.upper(), int(total_size), float(entry_price), mode, strategy)
        await update.message.reply_text(format_ladder_submission(plan), parse_mode="HTML")

    async def _execute_ladder(update, context):
        if not await _authorize_update(update):
            return
        if len(context.args) < 5:
            await update.message.reply_text("Usage: /execute_ladder <symbol> <side> <total_size> <entry_price> <strategy> [mode]")
            return
        symbol, side, total_size, entry_price, strategy = context.args[:5]
        mode = context.args[5] if len(context.args) >= 6 else config_service.get_execution_mode()
        plan = await live_execution_service.submit_stock_ladder(symbol.upper(), side.upper(), int(total_size), float(entry_price), mode, strategy)
        result = await broker_ladder_service.submit_stock_ladder(symbol.upper(), side.upper(), plan["entries"])
        await update.message.reply_text(format_ladder_execution_result(result), parse_mode="HTML")

    async def _set_profile_value(update, context):
        if not await _authorize_update(update):
            return
        if len(context.args) != 4:
            await update.message.reply_text("Usage: /set_profile_exec <mode> <strategy> <field> <value>")
            return
        mode, strategy, field, raw_value = context.args
        try:
            value = int(raw_value) if field in {"ladder_steps", "min_volume"} else float(raw_value)
        except Exception:
            value = raw_value
        profile = profile_store.set_profile(mode, strategy, {field: value})
        await update.message.reply_text(format_profile_execution_status(mode, strategy, profile), parse_mode="HTML")

    async def _pending_text(update, context):
        if context.user_data.get("pending_exec_profile_edit"):
            if update.effective_chat.id != admin_chat_id:
                await update.message.reply_text("Unauthorized.")
                context.user_data.pop("pending_exec_profile_edit", None)
                return
            pending = context.user_data.pop("pending_exec_profile_edit")
            raw_value = (update.message.text or "").strip()
            field = pending["field"]
            try:
                value = int(raw_value) if field in {"ladder_steps", "min_volume"} else float(raw_value)
            except Exception:
                value = raw_value
            profile = profile_store.set_profile(pending["mode"], pending["strategy"], {field: value})
            await update.message.reply_text(format_profile_execution_status(pending["mode"], pending["strategy"], profile), parse_mode="HTML", reply_markup=build_execution_profile_edit_keyboard(pending["mode"], pending["strategy"]))

    async def _guarded_callback(update, context):
        query = update.callback_query
        await query.answer()
        if update.effective_chat.id != admin_chat_id:
            await query.answer("Unauthorized", show_alert=True)
            return

        data = query.data or ""
        if data.startswith(("a|", "p|", "r|")):
            await handle_trade_callback(update, context, app_services)
            return
        if data == "cp|back":
            context.user_data.pop("pending_exec_profile_edit", None)
            await query.edit_message_text("Control Panel", reply_markup=build_control_panel_keyboard())
            return
        if data == "cp|execution_menu":
            await query.edit_message_text(format_execution_settings(_get_execution_settings()), parse_mode="HTML", reply_markup=build_execution_menu_keyboard())
            return
        if data == "cp|options_menu":
            settings = _get_options_settings()
            await query.edit_message_text(format_options_settings(settings), parse_mode="HTML", reply_markup=build_options_menu_keyboard(settings))
            return
        if data == "cp|ml_menu":
            await query.edit_message_text("ML / Analytics Menu", reply_markup=build_ml_menu_keyboard())
            return
        if data == "cp|exec_profiles":
            states = config_service.get_strategy_states()
            strategies = list(states.keys()) or ["breakout_box"]
            await query.edit_message_text("Execution Profiles", reply_markup=build_execution_profile_menu_keyboard(config_service.get_execution_mode(), strategies))
            return
        if data.startswith("ep|view|"):
            _, _, mode, strategy = data.split("|", 3)
            profile = profile_store.get_profile(mode, strategy)
            await query.edit_message_text(format_profile_execution_status(mode, strategy, profile), parse_mode="HTML", reply_markup=build_execution_profile_edit_keyboard(mode, strategy))
            return
        if data.startswith("ep|edit|"):
            _, _, mode, strategy, field = data.split("|", 4)
            context.user_data["pending_exec_profile_edit"] = {"mode": mode, "strategy": strategy, "field": field}
            await query.message.reply_text(f"Send new value for {mode}.{strategy}.{field}\nUse /cancel to stop.")
            return
        if data.startswith("exec|"):
            action = data.split("|", 1)[1]
            if action == "submit_ladder":
                plan = await live_execution_service.submit_stock_ladder("SPY", "LONG", 120, 10.0, config_service.get_execution_mode(), "breakout_box")
                await query.edit_message_text(format_ladder_submission(plan), parse_mode="HTML", reply_markup=build_execution_menu_keyboard())
                return
            if action == "open_trails":
                await query.edit_message_text(format_open_trails(trailing_stop_service.list_positions()), parse_mode="HTML", reply_markup=build_execution_menu_keyboard())
                return
        if data.startswith("opt|"):
            action = data.split("|", 1)[1]
            settings = _get_options_settings()
            if action == "toggle":
                settings = _update_options_settings(enabled=not settings.get("enabled", False))
                await query.edit_message_text(format_options_settings(settings), parse_mode="HTML", reply_markup=build_options_menu_keyboard(settings))
                return
            if action == "iv":
                await query.edit_message_text(format_iv_status(iv_analyzer.summarize_chain(_get_option_chain_rows())), parse_mode="HTML", reply_markup=build_options_menu_keyboard(settings))
                return
            if action == "flow":
                await query.edit_message_text(format_flow_status(flow_analyzer.summarize(_get_options_flow_rows())), parse_mode="HTML", reply_markup=build_options_menu_keyboard(settings))
                return
            if action == "chain":
                await query.edit_message_text(format_chain_summary(chain_service.summarize_chain(_get_option_chain_rows())), parse_mode="HTML", reply_markup=build_options_menu_keyboard(settings))
                return
            if action == "refresh_chain":
                symbol = settings.get("chain_symbol", "SPY")
                if app_services.get("tradier_client") is None:
                    await query.edit_message_text("Tradier client not configured.", reply_markup=build_options_menu_keyboard(settings))
                    return
                payload = await options_chain_ingest.refresh_chain(symbol)
                await query.edit_message_text(format_chain_summary(payload["summary"]), parse_mode="HTML", reply_markup=build_options_menu_keyboard(settings))
                return

        await query.edit_message_text("Unknown control panel action.", reply_markup=build_control_panel_keyboard())

    return [
        CommandHandler("start", start_command),
        CommandHandler("panel", panel_command),
        CommandHandler("ml_weights", _ml_weights),
        CommandHandler("sector_status", _sector_status),
        CommandHandler("flow_alerts", _flow_alerts),
        CommandHandler("iv_status", _iv_status),
        CommandHandler("refresh_option_chain", _refresh_option_chain),
        CommandHandler("chain_status", _chain_status),
        CommandHandler("trail_status", _trail_status),
        CommandHandler("sync_positions", _sync_positions),
        CommandHandler("profile_exec_status", _profile_exec_status),
        CommandHandler("submit_ladder", _submit_ladder),
        CommandHandler("execute_ladder", _execute_ladder),
        CommandHandler("set_profile_exec", _set_profile_value),
        CommandHandler("cancel", cancel_command),
        MessageHandler(filters.TEXT & ~filters.COMMAND, _pending_text),
        CallbackQueryHandler(_guarded_callback),
    ]
