from __future__ import annotations

import json
from typing import Any

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
    build_filter_categories_keyboard,
    build_filter_fields_keyboard,
    build_filter_profile_menu_keyboard,
    build_ml_menu_keyboard,
    build_mode_keyboard,
    build_options_menu_keyboard,
    build_presets_keyboard,
    build_scan_menu_keyboard,
    build_strategies_keyboard,
)
from .formatters import (
    format_chain_summary,
    format_execution_settings,
    format_exit_ladder_submission,
    format_filter_profile_status,
    format_flow_status,
    format_iv_status,
    format_ladder_execution_result,
    format_ladder_submission,
    format_ml_weights,
    format_mode_status,
    format_open_trails,
    format_options_settings,
    format_passing_rows,
    format_position_sync_result,
    format_profile_execution_status,
    format_scan_overview,
    format_scan_status,
    format_sector_status,
    format_snapshot_status,
    format_strategy_status,
)


SCAN_TYPE_TO_PROFILE = {
    "market": "overall",
    "overall": "overall",
    "scan": "overall",
    "premarket": "premarket",
    "midday": "midday",
    "overnight": "overnight",
}


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


def _coerce_scalar(raw_value: str) -> Any:
    raw = raw_value.strip()
    lowered = raw.lower()
    if lowered in {"true", "on", "yes", "1"}:
        return True
    if lowered in {"false", "off", "no", "0"}:
        return False
    try:
        if "." in raw:
            return float(raw)
        return int(raw)
    except Exception:
        return raw


async def start_command(update, context):
    await update.message.reply_text("Bot online.")


async def panel_command(update, context):
    await update.message.reply_text("Control Panel", reply_markup=build_control_panel_keyboard())


async def scans_command(update, context):
    await update.message.reply_text("Scan Menu", reply_markup=build_scan_menu_keyboard())


async def cancel_command(update, context):
    context.user_data.pop("pending_exec_profile_edit", None)
    context.user_data.pop("pending_filter_edit", None)
    await update.message.reply_text("Canceled.")


def build_handlers(app_services, config_service, admin_chat_id: int):
    settings_repo = config_service.settings_repo
    sector_analyzer = SectorAnalyzer()
    flow_analyzer = OptionsFlowAnalyzer()
    iv_analyzer = IVAnalyzer()
    chain_service = OptionsChainService()
    profile_store = StrategyExecutionProfiles(settings_repo)
    trailing_stop_service = app_services.get("trailing_stop_service") or TrailingStopService(settings_repo)
    options_chain_ingest = app_services.get("options_chain_ingest_service") or OptionsChainIngestService(settings_repo, app_services.get("tradier_client"))
    live_execution_service = app_services.get("live_execution_service")
    broker_ladder_service = app_services.get("broker_ladder_service") or BrokerLadderService(app_services.get("execution_router"))
    position_sync_service = app_services.get("position_sync_service") or PositionSyncService(
        trailing_stop_service,
        alpaca_client=app_services.get("alpaca_client"),
        tradier_client=app_services.get("tradier_client"),
    )
    scanner = app_services.get("scanner")
    discovery = app_services.get("discovery_service")

    def _get_ui_settings(name: str, default: dict) -> dict:
        overrides = settings_repo.get_filter_overrides()
        value = overrides.get(_meta_key(name))
        parsed = _parse_meta_value(value)
        merged = dict(default)
        if isinstance(parsed, dict):
            merged.update(parsed)
        return merged

    def _set_ui_settings(name: str, payload: dict) -> dict:
        settings_repo.set_filter_override(_meta_key(name), json.dumps(payload))
        return payload

    def _get_execution_settings() -> dict:
        return _get_ui_settings(
            "execution_settings",
            {
                "risk_pct": 0.75,
                "atr_multiplier": 1.0,
                "position_mode": "auto",
                "max_spread_pct": 0.03,
                "min_volume": 500000,
                "max_slippage_pct": 0.02,
                "ladder_steps": 3,
                "ladder_spacing_pct": 0.01,
                "trail_type": "percent",
                "trail_value": 0.02,
            },
        )

    def _update_execution_settings(**updates) -> dict:
        current = _get_execution_settings()
        current.update(updates)
        return _set_ui_settings("execution_settings", current)

    def _get_options_settings() -> dict:
        return _get_ui_settings(
            "options_settings",
            {
                "enabled": False,
                "delta_min": 0.30,
                "delta_max": 0.70,
                "min_open_interest": 1000,
                "expiry_preference": "weekly",
                "chain_symbol": "SPY",
            },
        )

    def _update_options_settings(**updates) -> dict:
        current = _get_options_settings()
        current.update(updates)
        return _set_ui_settings("options_settings", current)

    def _get_ml_weights() -> dict:
        return _get_ui_settings("ml_weights", {})

    def _set_ml_weights(weights: dict) -> dict:
        return _set_ui_settings("ml_weights", weights)

    def _get_option_chain_rows() -> list[dict]:
        value = _get_ui_settings("last_option_chain", {"rows": []})
        return list(value.get("rows", []))

    def _get_options_flow_rows() -> list[dict]:
        value = _get_ui_settings("options_flow_rows", {"rows": []})
        return list(value.get("rows", []))

    def _active_scan_type(context) -> str:
        return str(context.user_data.get("last_scan_type") or "market")

    def _set_active_scan_type(context, scan_type: str) -> None:
        context.user_data["last_scan_type"] = scan_type

    def _profile_from_scan(scan_type: str) -> str:
        return SCAN_TYPE_TO_PROFILE.get(scan_type, scan_type if scan_type in SCAN_TYPE_TO_PROFILE.values() else "overall")

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

    async def _run_scan(scan_type: str, context, *, refresh_snapshot: bool = False) -> str:
        scan_type = scan_type.lower()
        _set_active_scan_type(context, scan_type)

        if scan_type in {"market", "premarket", "midday", "overnight"} and refresh_snapshot and discovery is not None:
            await discovery.get_candidate_rows(scan_type, force_refresh=True)

        if scan_type == "market":
            payload = await scanner.scan_market_overview()
            return format_scan_overview(scan_type, payload)
        if scan_type == "premarket":
            payload = await scanner.scan_premarket_overview()
            return format_scan_overview(scan_type, payload)
        if scan_type == "midday":
            payload = await scanner.scan_midday_overview()
            return format_scan_overview(scan_type, payload)
        if scan_type == "overnight":
            payload = await scanner.scan_overnight_overview()
            return format_scan_overview(scan_type, payload)
        if scan_type == "news":
            payload = await scanner.scan_news_overview()
            return format_scan_overview(scan_type, payload)
        if scan_type == "events":
            payload = await scanner.scan_events_overview()
            return format_scan_overview(scan_type, payload)
        if scan_type == "catalyst":
            payload = await scanner.scan_catalyst_overview()
            return format_scan_overview(scan_type, payload)
        if scan_type == "full":
            payload = await scanner.scan_full_overview()
            parts = [
                format_scan_overview("premarket", payload.get("premarket", {})),
                format_scan_overview("market", payload.get("market", {})),
                format_scan_overview("news", payload.get("news", {})),
                format_scan_overview("events", payload.get("events", {})),
            ]
            return "\n\n".join(parts)
        return "Unknown scan type."

    async def _scan_status_text(context) -> str:
        return format_scan_status(scanner.get_last_scan_stats() if scanner is not None else {})

    async def _snapshot_status_text(context, profile: str | None = None) -> str:
        profile = profile or _profile_from_scan(_active_scan_type(context))
        if discovery is None:
            return "Snapshot service unavailable."
        status = await discovery.snapshot_status(profile)
        return format_snapshot_status(profile, status)

    async def _passers_text(context, scan_type: str | None = None, limit: int = 12) -> str:
        scan_type = scan_type or _active_scan_type(context)
        if discovery is None:
            return "Passer discovery unavailable."
        rows = await discovery.get_candidate_rows(scan_type, force_refresh=False)
        return format_passing_rows(scan_type, rows, limit=limit)

    async def _ml_weights(update, context):
        if await _authorize_update(update):
            await update.message.reply_text(format_ml_weights(_get_ml_weights()), parse_mode="HTML")

    async def _set_ml_weight(update, context):
        if not await _authorize_update(update):
            return
        if len(context.args) != 2:
            await update.message.reply_text("Usage: /set_ml_weight <name> <value>")
            return
        name, raw_value = context.args
        weights = _get_ml_weights()
        weights[name] = _coerce_scalar(raw_value)
        _set_ml_weights(weights)
        await update.message.reply_text(format_ml_weights(weights), parse_mode="HTML")

    async def _sector_status(update, context):
        if not await _authorize_update(update):
            return
        rows = await discovery.get_candidate_rows("market", force_refresh=False) if discovery is not None else []
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
        symbol = context.args[0].upper() if len(context.args) >= 1 else _get_options_settings().get("chain_symbol", "SPY")
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
        rows = await position_sync_service.sync_live_positions()
        if not rows or set(rows.keys()) <= {"alpaca_error", "tradier_error"}:
            rows = await position_sync_service.sync_demo_positions()
        await update.message.reply_text(format_position_sync_result(rows), parse_mode="HTML")

    async def _profile_exec_status(update, context):
        if not await _authorize_update(update):
            return
        mode = context.args[0] if len(context.args) >= 1 else config_service.get_execution_mode()
        strategy = context.args[1] if len(context.args) >= 2 else "Breakout Box"
        normalized_mode = profile_store.normalize_mode(mode)
        profile = profile_store.get_profile(normalized_mode, strategy)
        await update.message.reply_text(
            format_profile_execution_status(normalized_mode, profile_store.display_strategy(strategy), profile),
            parse_mode="HTML",
        )

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
        profile = profile_store.set_profile(mode, strategy, {field: _coerce_scalar(raw_value)})
        await update.message.reply_text(
            format_profile_execution_status(profile_store.normalize_mode(mode), profile_store.display_strategy(strategy), profile),
            parse_mode="HTML",
        )

    async def _options_on(update, context):
        if not await _authorize_update(update):
            return
        settings = _get_options_settings()
        if context.args:
            enabled = str(context.args[0]).lower() in {"true", "on", "1", "yes"}
        else:
            enabled = not bool(settings.get("enabled", False))
        settings = _update_options_settings(enabled=enabled)
        await update.message.reply_text(format_options_settings(settings), parse_mode="HTML")

    async def _set_delta_range(update, context):
        if not await _authorize_update(update):
            return
        if len(context.args) != 2:
            await update.message.reply_text("Usage: /set_delta_range <min> <max>")
            return
        settings = _update_options_settings(delta_min=float(context.args[0]), delta_max=float(context.args[1]))
        await update.message.reply_text(format_options_settings(settings), parse_mode="HTML")

    async def _set_min_oi(update, context):
        if not await _authorize_update(update):
            return
        if len(context.args) != 1:
            await update.message.reply_text("Usage: /set_min_oi <value>")
            return
        settings = _update_options_settings(min_open_interest=int(context.args[0]))
        await update.message.reply_text(format_options_settings(settings), parse_mode="HTML")

    async def _set_expiry(update, context):
        if not await _authorize_update(update):
            return
        if len(context.args) != 1:
            await update.message.reply_text("Usage: /set_expiry <weekly|monthly|YYYY-MM-DD>")
            return
        settings = _update_options_settings(expiry_preference=context.args[0])
        await update.message.reply_text(format_options_settings(settings), parse_mode="HTML")

    async def _set_risk_pct(update, context):
        if not await _authorize_update(update):
            return
        if len(context.args) != 1:
            await update.message.reply_text("Usage: /set_risk_pct <value>")
            return
        settings = _update_execution_settings(risk_pct=float(context.args[0]))
        await update.message.reply_text(format_execution_settings(settings), parse_mode="HTML")

    async def _set_atr_multiplier(update, context):
        if not await _authorize_update(update):
            return
        if len(context.args) != 1:
            await update.message.reply_text("Usage: /set_atr_multiplier <value>")
            return
        settings = _update_execution_settings(atr_multiplier=float(context.args[0]))
        await update.message.reply_text(format_execution_settings(settings), parse_mode="HTML")

    async def _set_position_mode(update, context):
        if not await _authorize_update(update):
            return
        if len(context.args) != 1:
            await update.message.reply_text("Usage: /set_position_mode <auto|stock|options>")
            return
        settings = _update_execution_settings(position_mode=context.args[0])
        await update.message.reply_text(format_execution_settings(settings), parse_mode="HTML")

    async def _scan_command(update, context, scan_type: str):
        if not await _authorize_update(update):
            return
        await update.message.reply_text(await _run_scan(scan_type, context), parse_mode="HTML")

    async def _scan(update, context):
        scan_type = context.args[0].lower() if context.args else "market"
        await _scan_command(update, context, scan_type)

    async def _scan_market(update, context):
        await _scan_command(update, context, "market")

    async def _scan_premarket(update, context):
        await _scan_command(update, context, "premarket")

    async def _scan_midday(update, context):
        await _scan_command(update, context, "midday")

    async def _scan_overnight(update, context):
        await _scan_command(update, context, "overnight")

    async def _scan_news(update, context):
        await _scan_command(update, context, "news")

    async def _scan_events(update, context):
        await _scan_command(update, context, "events")

    async def _scan_catalyst(update, context):
        await _scan_command(update, context, "catalyst")

    async def _scan_status(update, context):
        if not await _authorize_update(update):
            return
        await update.message.reply_text(await _scan_status_text(context), parse_mode="HTML")

    async def _refresh_snapshot(update, context):
        if not await _authorize_update(update):
            return
        scan_type = context.args[0].lower() if context.args else _active_scan_type(context)
        if discovery is None:
            await update.message.reply_text("Snapshot service unavailable.")
            return
        await discovery.get_candidate_rows(scan_type, force_refresh=True)
        await update.message.reply_text(await _snapshot_status_text(context, _profile_from_scan(scan_type)), parse_mode="HTML")

    async def _snapshot_status(update, context):
        if not await _authorize_update(update):
            return
        profile = context.args[0].lower() if context.args else None
        await update.message.reply_text(await _snapshot_status_text(context, profile), parse_mode="HTML")

    async def _show_passers(update, context):
        if not await _authorize_update(update):
            return
        scan_type = context.args[0].lower() if context.args else _active_scan_type(context)
        limit = int(context.args[1]) if len(context.args) >= 2 else 12
        await update.message.reply_text(await _passers_text(context, scan_type, limit=limit), parse_mode="HTML")

    async def _pending_text(update, context):
        if update.effective_chat.id != admin_chat_id:
            return

        pending_profile = context.user_data.get("pending_exec_profile_edit")
        if pending_profile:
            context.user_data.pop("pending_exec_profile_edit", None)
            field = pending_profile["field"]
            profile = profile_store.set_profile(
                pending_profile["mode"],
                pending_profile["strategy"],
                {field: _coerce_scalar((update.message.text or "").strip())},
            )
            await update.message.reply_text(
                format_profile_execution_status(
                    profile_store.normalize_mode(pending_profile["mode"]),
                    profile_store.display_strategy(pending_profile["strategy"]),
                    profile,
                ),
                parse_mode="HTML",
                reply_markup=build_execution_profile_edit_keyboard(
                    profile_store.normalize_mode(pending_profile["mode"]),
                    pending_profile["strategy"],
                ),
            )
            return

        pending_filter = context.user_data.get("pending_filter_edit")
        if pending_filter:
            context.user_data.pop("pending_filter_edit", None)
            profile = pending_filter["profile"]
            category = pending_filter["category"]
            field = pending_filter["field"]
            try:
                config_service.set_filter_value(category, field, update.message.text or "", profile=profile)
                values = config_service.get_filter_fields(category, profile=profile)
                await update.message.reply_text(
                    f"Updated {profile}.{category}.{field}",
                    reply_markup=build_filter_fields_keyboard(profile, category, values),
                )
            except Exception as exc:
                await update.message.reply_text(f"Failed to update filter: {exc}")

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
            context.user_data.pop("pending_filter_edit", None)
            await query.edit_message_text("Control Panel", reply_markup=build_control_panel_keyboard())
            return

        if data == "cp|scan_menu":
            await query.edit_message_text("Scan Menu", reply_markup=build_scan_menu_keyboard())
            return

        if data == "cp|presets":
            active_profile = config_service.get_active_filter_profile()
            current = config_service.get_profile_preset(active_profile)
            await query.edit_message_text(
                format_filter_profile_status(active_profile, current),
                parse_mode="HTML",
                reply_markup=build_presets_keyboard(config_service.get_available_presets(), current),
            )
            return

        if data == "cp|mode":
            await query.edit_message_text(
                format_mode_status(config_service.get_execution_mode()),
                parse_mode="HTML",
                reply_markup=build_mode_keyboard(config_service.get_execution_mode()),
            )
            return

        if data == "cp|strategies":
            states = config_service.get_strategy_states()
            await query.edit_message_text(
                format_strategy_status(states),
                parse_mode="HTML",
                reply_markup=build_strategies_keyboard(states),
            )
            return

        if data == "cp|filters":
            active_profile = config_service.get_active_filter_profile()
            await query.edit_message_text(
                format_filter_profile_status(active_profile, config_service.get_profile_preset(active_profile)),
                parse_mode="HTML",
                reply_markup=build_filter_profile_menu_keyboard(config_service.get_profile_preset_map(), active_profile),
            )
            return

        if data == "cp|execution_menu":
            await query.edit_message_text(
                format_execution_settings(_get_execution_settings()),
                parse_mode="HTML",
                reply_markup=build_execution_menu_keyboard(),
            )
            return

        if data == "cp|options_menu":
            settings = _get_options_settings()
            await query.edit_message_text(
                format_options_settings(settings),
                parse_mode="HTML",
                reply_markup=build_options_menu_keyboard(settings),
            )
            return

        if data == "cp|ml_menu":
            await query.edit_message_text("ML / Analytics Menu", reply_markup=build_ml_menu_keyboard())
            return

        if data == "cp|exec_profiles":
            states = config_service.get_strategy_states()
            strategies = list(states.keys()) or ["Breakout Box"]
            await query.edit_message_text(
                "Execution Profiles",
                reply_markup=build_execution_profile_menu_keyboard(config_service.get_execution_mode(), strategies),
            )
            return

        if data.startswith("scan|"):
            action = data.split("|", 1)[1]
            if action in {"market", "premarket", "midday", "overnight", "news", "events", "catalyst", "full"}:
                text = await _run_scan(action, context)
                await query.edit_message_text(text, parse_mode="HTML", reply_markup=build_scan_menu_keyboard())
                return
            if action == "status":
                await query.edit_message_text(await _scan_status_text(context), parse_mode="HTML", reply_markup=build_scan_menu_keyboard())
                return
            if action == "refresh_snapshot":
                scan_type = _active_scan_type(context)
                if discovery is None:
                    await query.edit_message_text("Snapshot service unavailable.", reply_markup=build_scan_menu_keyboard())
                    return
                await discovery.get_candidate_rows(scan_type, force_refresh=True)
                await query.edit_message_text(
                    await _snapshot_status_text(context, _profile_from_scan(scan_type)),
                    parse_mode="HTML",
                    reply_markup=build_scan_menu_keyboard(),
                )
                return
            if action == "snapshot_status":
                await query.edit_message_text(
                    await _snapshot_status_text(context),
                    parse_mode="HTML",
                    reply_markup=build_scan_menu_keyboard(),
                )
                return
            if action == "passers":
                await query.edit_message_text(
                    await _passers_text(context),
                    parse_mode="HTML",
                    reply_markup=build_scan_menu_keyboard(),
                )
                return

        if data.startswith("set|preset|"):
            preset_name = data.split("|", 2)[2]
            active_profile = config_service.get_active_filter_profile()
            config_service.set_profile_preset(active_profile, preset_name)
            await query.edit_message_text(
                format_filter_profile_status(active_profile, preset_name),
                parse_mode="HTML",
                reply_markup=build_presets_keyboard(config_service.get_available_presets(), preset_name),
            )
            return

        if data.startswith("set|mode|"):
            mode = data.split("|", 2)[2]
            config_service.set_execution_mode(mode)
            await query.edit_message_text(
                format_mode_status(mode),
                parse_mode="HTML",
                reply_markup=build_mode_keyboard(mode),
            )
            return

        if data.startswith("toggle|strategy|"):
            strategy_name = data.split("|", 2)[2]
            states = config_service.get_strategy_states()
            new_value = not bool(states.get(strategy_name, True))
            settings_repo.set_strategy_state(strategy_name, new_value)
            updated = config_service.get_strategy_states()
            await query.edit_message_text(
                format_strategy_status(updated),
                parse_mode="HTML",
                reply_markup=build_strategies_keyboard(updated),
            )
            return

        if data.startswith("fprofile|"):
            profile = data.split("|", 1)[1]
            config_service.set_active_filter_profile(profile)
            values = config_service.resolve_filters(profile=profile)
            await query.edit_message_text(
                format_filter_profile_status(profile, config_service.get_profile_preset(profile)),
                parse_mode="HTML",
                reply_markup=build_filter_categories_keyboard(values, profile),
            )
            return

        if data.startswith("fcat|"):
            _, profile, category = data.split("|", 2)
            values = config_service.get_filter_fields(category, profile=profile)
            await query.edit_message_text(
                f"{profile.title()} / {category.title()}",
                reply_markup=build_filter_fields_keyboard(profile, category, values),
            )
            return

        if data.startswith("fedit|"):
            _, profile, category, field = data.split("|", 3)
            context.user_data["pending_filter_edit"] = {"profile": profile, "category": category, "field": field}
            await query.message.reply_text(f"Send new value for {profile}.{category}.{field}\nUse /cancel to stop.")
            return

        if data == "freset|all":
            config_service.reset_all_filter_overrides()
            active_profile = config_service.get_active_filter_profile()
            await query.edit_message_text(
                format_filter_profile_status(active_profile, config_service.get_profile_preset(active_profile)),
                parse_mode="HTML",
                reply_markup=build_filter_profile_menu_keyboard(config_service.get_profile_preset_map(), active_profile),
            )
            return

        if data.startswith("freset_profile|"):
            profile = data.split("|", 1)[1]
            config_service.reset_filter_overrides(profile=profile)
            values = config_service.resolve_filters(profile=profile)
            await query.edit_message_text(
                format_filter_profile_status(profile, config_service.get_profile_preset(profile)),
                parse_mode="HTML",
                reply_markup=build_filter_categories_keyboard(values, profile),
            )
            return

        if data.startswith("freset|"):
            _, profile, category = data.split("|", 2)
            config_service.reset_filter_category(category, profile=profile)
            values = config_service.get_filter_fields(category, profile=profile)
            await query.edit_message_text(
                f"{profile.title()} / {category.title()}",
                reply_markup=build_filter_fields_keyboard(profile, category, values),
            )
            return

        if data.startswith("ep|view|"):
            _, _, mode, strategy = data.split("|", 3)
            normalized_mode = profile_store.normalize_mode(mode)
            profile = profile_store.get_profile(normalized_mode, strategy)
            await query.edit_message_text(
                format_profile_execution_status(normalized_mode, profile_store.display_strategy(strategy), profile),
                parse_mode="HTML",
                reply_markup=build_execution_profile_edit_keyboard(normalized_mode, strategy),
            )
            return

        if data.startswith("ep|edit|"):
            _, _, mode, strategy, field = data.split("|", 4)
            context.user_data["pending_exec_profile_edit"] = {"mode": mode, "strategy": strategy, "field": field}
            await query.message.reply_text(f"Send new value for {mode}.{strategy}.{field}\nUse /cancel to stop.")
            return

        if data.startswith("exec|"):
            action = data.split("|", 1)[1]
            if action in {"show", "safeguards"}:
                await query.edit_message_text(
                    format_execution_settings(_get_execution_settings()),
                    parse_mode="HTML",
                    reply_markup=build_execution_menu_keyboard(),
                )
                return
            if action == "ladder":
                plan = await live_execution_service.submit_stock_ladder(
                    "SPY",
                    "LONG",
                    120,
                    10.0,
                    config_service.get_execution_mode(),
                    "Breakout Box",
                )
                await query.edit_message_text(
                    format_ladder_submission(plan),
                    parse_mode="HTML",
                    reply_markup=build_execution_menu_keyboard(),
                )
                return
            if action == "trailing" or action == "open_trails":
                await query.edit_message_text(
                    format_open_trails(trailing_stop_service.list_positions()),
                    parse_mode="HTML",
                    reply_markup=build_execution_menu_keyboard(),
                )
                return
            if action == "submit_ladder":
                plan = await live_execution_service.build_exit_ladder(
                    "SPY",
                    "LONG",
                    120,
                    10.0,
                    9.5,
                    config_service.get_execution_mode(),
                    "Breakout Box",
                )
                await query.edit_message_text(
                    format_exit_ladder_submission(plan),
                    parse_mode="HTML",
                    reply_markup=build_execution_menu_keyboard(),
                )
                return

        if data.startswith("opt|"):
            action = data.split("|", 1)[1]
            settings = _get_options_settings()
            if action == "toggle":
                settings = _update_options_settings(enabled=not settings.get("enabled", False))
                await query.edit_message_text(
                    format_options_settings(settings),
                    parse_mode="HTML",
                    reply_markup=build_options_menu_keyboard(settings),
                )
                return
            if action == "show":
                await query.edit_message_text(
                    format_options_settings(settings),
                    parse_mode="HTML",
                    reply_markup=build_options_menu_keyboard(settings),
                )
                return
            if action == "iv":
                await query.edit_message_text(
                    format_iv_status(iv_analyzer.summarize_chain(_get_option_chain_rows())),
                    parse_mode="HTML",
                    reply_markup=build_options_menu_keyboard(settings),
                )
                return
            if action == "flow":
                await query.edit_message_text(
                    format_flow_status(flow_analyzer.summarize(_get_options_flow_rows())),
                    parse_mode="HTML",
                    reply_markup=build_options_menu_keyboard(settings),
                )
                return
            if action == "chain":
                await query.edit_message_text(
                    format_chain_summary(chain_service.summarize_chain(_get_option_chain_rows())),
                    parse_mode="HTML",
                    reply_markup=build_options_menu_keyboard(settings),
                )
                return
            if action == "refresh_chain":
                symbol = settings.get("chain_symbol", "SPY")
                if app_services.get("tradier_client") is None:
                    await query.edit_message_text("Tradier client not configured.", reply_markup=build_options_menu_keyboard(settings))
                    return
                payload = await options_chain_ingest.refresh_chain(symbol)
                await query.edit_message_text(
                    format_chain_summary(payload["summary"]),
                    parse_mode="HTML",
                    reply_markup=build_options_menu_keyboard(settings),
                )
                return

        if data.startswith("ml|"):
            action = data.split("|", 1)[1]
            if action == "show":
                await query.edit_message_text(format_ml_weights(_get_ml_weights()), parse_mode="HTML", reply_markup=build_ml_menu_keyboard())
                return
            if action == "sector":
                rows = await discovery.get_candidate_rows("market", force_refresh=False) if discovery is not None else []
                symbols = [row["symbol"] for row in rows[:25]]
                await query.edit_message_text(
                    format_sector_status(sector_analyzer.summarize(symbols)),
                    parse_mode="HTML",
                    reply_markup=build_ml_menu_keyboard(),
                )
                return
            if action == "flow":
                await query.edit_message_text(
                    format_flow_status(flow_analyzer.summarize(_get_options_flow_rows())),
                    parse_mode="HTML",
                    reply_markup=build_ml_menu_keyboard(),
                )
                return
            if action == "iv":
                await query.edit_message_text(
                    format_iv_status(iv_analyzer.summarize_chain(_get_option_chain_rows())),
                    parse_mode="HTML",
                    reply_markup=build_ml_menu_keyboard(),
                )
                return

        await query.edit_message_text("Unknown control panel action.", reply_markup=build_control_panel_keyboard())

    return [
        CommandHandler("start", start_command),
        CommandHandler("panel", panel_command),
        CommandHandler("scans", scans_command),
        CommandHandler("scan_menu", scans_command),
        CommandHandler("scan", _scan),
        CommandHandler("scan_market", _scan_market),
        CommandHandler("scan_premarket", _scan_premarket),
        CommandHandler("scan_midday", _scan_midday),
        CommandHandler("scan_overnight", _scan_overnight),
        CommandHandler("scan_news", _scan_news),
        CommandHandler("scan_events", _scan_events),
        CommandHandler("scan_catalyst", _scan_catalyst),
        CommandHandler("scan_status", _scan_status),
        CommandHandler("refresh_snapshot", _refresh_snapshot),
        CommandHandler("snapshot_status", _snapshot_status),
        CommandHandler("show_passers", _show_passers),
        CommandHandler("ml_weights", _ml_weights),
        CommandHandler("set_ml_weight", _set_ml_weight),
        CommandHandler("sector_status", _sector_status),
        CommandHandler("flow_alerts", _flow_alerts),
        CommandHandler("iv_status", _iv_status),
        CommandHandler("options_on", _options_on),
        CommandHandler("set_delta_range", _set_delta_range),
        CommandHandler("set_min_oi", _set_min_oi),
        CommandHandler("set_expiry", _set_expiry),
        CommandHandler("set_risk_pct", _set_risk_pct),
        CommandHandler("set_atr_multiplier", _set_atr_multiplier),
        CommandHandler("set_position_mode", _set_position_mode),
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
