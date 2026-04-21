from __future__ import annotations

import json

from telegram.ext import CallbackQueryHandler, CommandHandler, MessageHandler, filters

from execution.ladder_manager import LadderManager
from execution.multi_leg import MultiLegOrderBuilder
from execution.safeguards import ExecutionSafeguards
from execution.trailing_manager import TrailingManager
from services.iv_analyzer import IVAnalyzer
from services.options_chain_service import OptionsChainService
from services.options_flow_analyzer import OptionsFlowAnalyzer
from services.options_order_service import OptionsOrderService
from services.sector_analyzer import SectorAnalyzer

from .callbacks import handle_trade_callback
from .keyboards import (
    VALID_FILTER_CATEGORIES,
    build_control_panel_keyboard,
    build_execution_menu_keyboard,
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
    format_catalyst_scan,
    format_chain_summary,
    format_event_scan,
    format_execution_settings,
    format_flow_status,
    format_full_scan_summary,
    format_iv_status,
    format_ladder_preview,
    format_ml_weights,
    format_multileg_preview,
    format_news_scan,
    format_options_settings,
    format_passers,
    format_scan_status,
    format_sector_status,
    format_snapshot_status,
    format_trailing_preview,
)


def _format_filter_category(profile: str, category: str, values: dict) -> str:
    lines = [f"{profile.title()} / {category.title()} Filters", ""]
    for key, value in values.items():
        lines.append(f"- {key}: {value}")
    lines += ["", "Tap a field below to edit it."]
    return "\n".join(lines)


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


async def scans_command(update, context):
    await update.message.reply_text("Scan Menu", reply_markup=build_scan_menu_keyboard())


async def config_command(update, context, config_service):
    profile_map = config_service.get_profile_preset_map()
    await update.message.reply_text(
        f"Overall preset: {config_service.get_active_preset()}\n"
        f"Execution mode: {config_service.get_execution_mode()}\n"
        f"Filter profile: {config_service.get_active_filter_profile()}\n"
        f"Premarket preset: {profile_map['premarket']}\n"
        f"Midday preset: {profile_map['midday']}\n"
        f"Overnight preset: {profile_map['overnight']}"
    )


async def cancel_command(update, context):
    context.user_data.pop("pending_filter_edit", None)
    await update.message.reply_text("Canceled.")


def build_handlers(app_services, config_service, admin_chat_id: int):
    settings_repo = config_service.settings_repo
    sector_analyzer = SectorAnalyzer()
    flow_analyzer = OptionsFlowAnalyzer()
    iv_analyzer = IVAnalyzer()
    chain_service = OptionsChainService()
    ladder_manager = LadderManager()
    trailing_manager = TrailingManager()
    multileg_builder = MultiLegOrderBuilder()
    options_order_service = OptionsOrderService()

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
            },
        )

    def _update_options_settings(**updates) -> dict:
        current = _get_options_settings()
        current.update(updates)
        return _set_ui_settings("options_settings", current)

    def _get_ml_weights() -> dict:
        return _get_ui_settings("ml_weights", {})

    def _update_ml_weight(name: str, value: float) -> dict:
        current = _get_ml_weights()
        current[name] = value
        return _set_ui_settings("ml_weights", current)

    def _get_option_chain_rows() -> list[dict]:
        value = _get_ui_settings("last_option_chain", {"rows": []})
        return list(value.get("rows", []))

    def _get_options_flow_rows() -> list[dict]:
        value = _get_ui_settings("options_flow_rows", {"rows": []})
        return list(value.get("rows", []))

    async def _config(update, context):
        await config_command(update, context, config_service)

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

    async def _run_lane(update, context, method_name: str, label: str):
        if not await _authorize_update(update):
            return
        scanner = app_services.get("scanner")
        if scanner is None:
            await update.message.reply_text("Scanner service not available.")
            return
        await update.message.reply_text(f"Running {label}...")
        result = await getattr(scanner, method_name)()
        await update.message.reply_text(format_scan_status(result["stats"]) + f"\n\nCandidates returned: {len(result['candidates'])}", parse_mode="HTML")

    async def _scan(update, context):
        if not await _authorize_update(update):
            return
        scanner = app_services.get("scanner")
        if scanner is None:
            await update.message.reply_text("Scanner service not available.")
            return
        await update.message.reply_text("Running full scan...")
        summary = await scanner.scan_full_overview()
        await update.message.reply_text(format_full_scan_summary(summary), parse_mode="HTML")

    async def _scan_market(update, context):
        await _run_lane(update, context, "scan_market_overview", "market scan")

    async def _scan_premarket(update, context):
        await _run_lane(update, context, "scan_premarket_overview", "premarket scan")

    async def _scan_midday(update, context):
        await _run_lane(update, context, "scan_midday_overview", "midday scan")

    async def _scan_overnight(update, context):
        await _run_lane(update, context, "scan_overnight_overview", "overnight scan")

    async def _scan_news(update, context):
        if not await _authorize_update(update):
            return
        scanner = app_services.get("scanner")
        if scanner is None:
            await update.message.reply_text("Scanner service not available.")
            return
        await update.message.reply_text("Running news scan...")
        await update.message.reply_text(format_news_scan(await scanner.scan_news_overview()), parse_mode="HTML")

    async def _scan_events(update, context):
        if not await _authorize_update(update):
            return
        scanner = app_services.get("scanner")
        if scanner is None:
            await update.message.reply_text("Scanner service not available.")
            return
        await update.message.reply_text("Running events scan...")
        await update.message.reply_text(format_event_scan(await scanner.scan_events_overview()), parse_mode="HTML")

    async def _scan_catalyst(update, context):
        if not await _authorize_update(update):
            return
        scanner = app_services.get("scanner")
        if scanner is None:
            await update.message.reply_text("Scanner service not available.")
            return
        await update.message.reply_text("Running catalyst scan...")
        await update.message.reply_text(format_catalyst_scan(await scanner.scan_catalyst_overview()), parse_mode="HTML")

    async def _scan_status(update, context):
        if not await _authorize_update(update):
            return
        scanner = app_services.get("scanner")
        if scanner is None:
            await update.message.reply_text("Scanner service not available.")
            return
        await update.message.reply_text(format_scan_status(scanner.get_last_scan_stats()), parse_mode="HTML")

    async def _refresh_snapshot(update, context):
        if not await _authorize_update(update):
            return
        discovery = app_services.get("discovery_service")
        if discovery is None:
            await update.message.reply_text("Discovery service not available.")
            return
        profile = config_service.get_active_filter_profile()
        await update.message.reply_text(f"Refreshing snapshot for {profile}...")
        await discovery.get_snapshot(profile, force_refresh=True)
        await update.message.reply_text(format_snapshot_status(await discovery.snapshot_status(profile)), parse_mode="HTML")

    async def _snapshot_status(update, context):
        if not await _authorize_update(update):
            return
        discovery = app_services.get("discovery_service")
        if discovery is None:
            await update.message.reply_text("Discovery service not available.")
            return
        profile = config_service.get_active_filter_profile()
        await update.message.reply_text(format_snapshot_status(await discovery.snapshot_status(profile)), parse_mode="HTML")

    async def _show_passers(update, context):
        if not await _authorize_update(update):
            return
        discovery = app_services.get("discovery_service")
        if discovery is None:
            await update.message.reply_text("Discovery service not available.")
            return
        scan_type = "market"
        if context.args:
            candidate = context.args[0].strip().lower()
            if candidate in {"premarket", "market", "midday", "overnight"}:
                scan_type = candidate
        rows = await discovery.get_candidate_rows(scan_type, force_refresh=False)
        await update.message.reply_text(format_passers(scan_type, rows), parse_mode="HTML")

    async def _ml_weights(update, context):
        if not await _authorize_update(update):
            return
        await update.message.reply_text(format_ml_weights(_get_ml_weights()), parse_mode="HTML")

    async def _set_ml_weight(update, context):
        if not await _authorize_update(update):
            return
        if len(context.args) != 2:
            await update.message.reply_text("Usage: /set_ml_weight <factor> <value>")
            return
        factor = context.args[0].strip()
        value = float(context.args[1])
        weights = _update_ml_weight(factor, value)
        await update.message.reply_text(format_ml_weights(weights), parse_mode="HTML")

    async def _sector_status(update, context):
        if not await _authorize_update(update):
            return
        discovery = app_services.get("discovery_service")
        if discovery is None:
            await update.message.reply_text("Discovery service not available.")
            return
        rows = await discovery.get_candidate_rows("market", force_refresh=False)
        symbols = [row["symbol"] for row in rows[:25]]
        await update.message.reply_text(format_sector_status(sector_analyzer.summarize(symbols)), parse_mode="HTML")

    async def _flow_alerts(update, context):
        if not await _authorize_update(update):
            return
        await update.message.reply_text(format_flow_status(flow_analyzer.summarize(_get_options_flow_rows())), parse_mode="HTML")

    async def _iv_status(update, context):
        if not await _authorize_update(update):
            return
        await update.message.reply_text(format_iv_status(iv_analyzer.summarize_chain(_get_option_chain_rows())), parse_mode="HTML")

    async def _options_on(update, context):
        if not await _authorize_update(update):
            return
        settings = _update_options_settings(enabled=True)
        await update.message.reply_text(format_options_settings(settings), parse_mode="HTML")

    async def _set_delta_range(update, context):
        if not await _authorize_update(update):
            return
        if len(context.args) != 2:
            await update.message.reply_text("Usage: /set_delta_range <min> <max>")
            return
        delta_min = float(context.args[0])
        delta_max = float(context.args[1])
        if delta_min < 0 or delta_max > 1 or delta_min >= delta_max:
            await update.message.reply_text("Delta range must be between 0 and 1, with min < max.")
            return
        settings = _update_options_settings(delta_min=round(delta_min, 2), delta_max=round(delta_max, 2))
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
            await update.message.reply_text("Usage: /set_expiry weekly|monthly|any")
            return
        expiry = context.args[0].lower().strip()
        if expiry not in {"weekly", "monthly", "any"}:
            await update.message.reply_text("Expiry must be weekly, monthly, or any.")
            return
        settings = _update_options_settings(expiry_preference=expiry)
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
            await update.message.reply_text("Usage: /set_position_mode auto|fixed")
            return
        mode = context.args[0].lower().strip()
        if mode not in {"auto", "fixed"}:
            await update.message.reply_text("Position mode must be auto or fixed.")
            return
        settings = _update_execution_settings(position_mode=mode)
        await update.message.reply_text(format_execution_settings(settings), parse_mode="HTML")

    async def _pending_text(update, context):
        pending = context.user_data.get("pending_filter_edit")
        if not pending:
            return
        if update.effective_chat.id != admin_chat_id:
            await update.message.reply_text("Unauthorized.")
            context.user_data.pop("pending_filter_edit", None)
            return

        raw_value = (update.message.text or "").strip()
        profile = pending["profile"]
        category = pending["category"]
        field = pending["field"]

        try:
            new_value = config_service.set_filter_value(category, field, raw_value, profile=profile)
        except ValueError as exc:
            await update.message.reply_text(f"Invalid value for {profile}.{category}.{field}: {exc}\nSend a new value or /cancel.")
            return
        except Exception as exc:
            await update.message.reply_text(f"Could not update {profile}.{category}.{field}: {exc}\nSend /cancel to exit.")
            return

        context.user_data.pop("pending_filter_edit", None)
        values = config_service.get_filter_fields(category, profile=profile)
        await update.message.reply_text(f"Updated {profile}.{category}.{field} to {new_value}.", reply_markup=build_filter_fields_keyboard(profile, category, values))

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
            context.user_data.pop("pending_filter_edit", None)
            await query.edit_message_text("Control Panel", reply_markup=build_control_panel_keyboard())
            return

        if data == "cp|scan_menu":
            await query.edit_message_text("Scan Menu", reply_markup=build_scan_menu_keyboard())
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

        if data == "cp|presets":
            await query.edit_message_text(f"Select Overall Preset\nCurrent: {config_service.get_active_preset()}", reply_markup=build_presets_keyboard(config_service.get_available_presets(), config_service.get_active_preset()))
            return

        if data == "cp|mode":
            await query.edit_message_text(f"Select Mode\nCurrent: {config_service.get_execution_mode()}", reply_markup=build_mode_keyboard(config_service.get_execution_mode()))
            return

        if data == "cp|strategies":
            await query.edit_message_text("Strategies", reply_markup=build_strategies_keyboard(config_service.get_strategy_states()))
            return

        if data == "cp|filters":
            active_profile = config_service.get_active_filter_profile()
            await query.edit_message_text("Choose which scan preset you want to edit.", reply_markup=build_filter_profile_menu_keyboard(config_service.get_profile_preset_map(), active_profile))
            return

        if data.startswith("scan|"):
            scanner = app_services.get("scanner")
            discovery = app_services.get("discovery_service")
            action = data.split("|", 1)[1]

            if action == "market":
                result = await scanner.scan_market_overview()
                await query.edit_message_text(format_scan_status(result["stats"]), parse_mode="HTML", reply_markup=build_scan_menu_keyboard())
                return
            if action == "premarket":
                result = await scanner.scan_premarket_overview()
                await query.edit_message_text(format_scan_status(result["stats"]), parse_mode="HTML", reply_markup=build_scan_menu_keyboard())
                return
            if action == "midday":
                result = await scanner.scan_midday_overview()
                await query.edit_message_text(format_scan_status(result["stats"]), parse_mode="HTML", reply_markup=build_scan_menu_keyboard())
                return
            if action == "overnight":
                result = await scanner.scan_overnight_overview()
                await query.edit_message_text(format_scan_status(result["stats"]), parse_mode="HTML", reply_markup=build_scan_menu_keyboard())
                return
            if action == "news":
                await query.edit_message_text(format_news_scan(await scanner.scan_news_overview()), parse_mode="HTML", reply_markup=build_scan_menu_keyboard())
                return
            if action == "events":
                await query.edit_message_text(format_event_scan(await scanner.scan_events_overview()), parse_mode="HTML", reply_markup=build_scan_menu_keyboard())
                return
            if action == "catalyst":
                await query.edit_message_text(format_catalyst_scan(await scanner.scan_catalyst_overview()), parse_mode="HTML", reply_markup=build_scan_menu_keyboard())
                return
            if action == "full":
                await query.edit_message_text(format_full_scan_summary(await scanner.scan_full_overview()), parse_mode="HTML", reply_markup=build_scan_menu_keyboard())
                return
            if action == "status":
                await query.edit_message_text(format_scan_status(scanner.get_last_scan_stats()), parse_mode="HTML", reply_markup=build_scan_menu_keyboard())
                return
            if action == "refresh_snapshot":
                profile = config_service.get_active_filter_profile()
                await discovery.get_snapshot(profile, force_refresh=True)
                await query.edit_message_text(format_snapshot_status(await discovery.snapshot_status(profile)), parse_mode="HTML", reply_markup=build_scan_menu_keyboard())
                return
            if action == "snapshot_status":
                profile = config_service.get_active_filter_profile()
                await query.edit_message_text(format_snapshot_status(await discovery.snapshot_status(profile)), parse_mode="HTML", reply_markup=build_scan_menu_keyboard())
                return
            if action == "passers":
                rows = await discovery.get_candidate_rows("market", force_refresh=False)
                await query.edit_message_text(format_passers("market", rows), parse_mode="HTML", reply_markup=build_scan_menu_keyboard())
                return

        if data.startswith("exec|"):
            action = data.split("|", 1)[1]
            settings = _get_execution_settings()
            if action == "safeguards":
                guard = ExecutionSafeguards(settings)
                valid, message = guard.validate_trade({"price": 10, "bid": 9.98, "ask": 10.02, "volume": settings.get("min_volume", 500000)})
                text = format_execution_settings(settings) + f"\n\n<b>Safeguard Check:</b> {message} ({valid})"
                await query.edit_message_text(text, parse_mode="HTML", reply_markup=build_execution_menu_keyboard())
                return
            if action == "ladder":
                entries = ladder_manager.build_entry_ladder(entry_price=10.0, side="LONG", total_size=120, steps=settings.get("ladder_steps", 3), spacing_pct=settings.get("ladder_spacing_pct", 0.01))
                exits = ladder_manager.build_exit_ladder(entry_price=10.0, side="LONG", total_size=120, rr_targets=[1.0, 2.0, 3.0], risk_per_unit=0.5)
                await query.edit_message_text(format_ladder_preview({"entries": entries, "exits": exits}), parse_mode="HTML", reply_markup=build_execution_menu_keyboard())
                return
            if action == "trailing":
                state = trailing_manager.initial_state(entry_price=10.0, stop_loss=9.5, side="LONG", trail_type=settings.get("trail_type", "percent"), trail_value=settings.get("trail_value", 0.02))
                updated = trailing_manager.update(state, 10.8)
                await query.edit_message_text(format_trailing_preview(updated), parse_mode="HTML", reply_markup=build_execution_menu_keyboard())
                return
            await query.edit_message_text(format_execution_settings(settings), parse_mode="HTML", reply_markup=build_execution_menu_keyboard())
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
                summary = chain_service.summarize_chain(_get_option_chain_rows())
                await query.edit_message_text(format_chain_summary(summary), parse_mode="HTML", reply_markup=build_options_menu_keyboard(settings))
                return
            if action == "multileg":
                order = options_order_service.build_vertical_spread_order("ABC240621C00050000", "ABC240621C00055000", 1, debit=True)
                await query.edit_message_text(format_multileg_preview(order), parse_mode="HTML", reply_markup=build_options_menu_keyboard(settings))
                return
            await query.edit_message_text(format_options_settings(settings), parse_mode="HTML", reply_markup=build_options_menu_keyboard(settings))
            return

        if data.startswith("ml|"):
            action = data.split("|", 1)[1]
            if action == "show":
                await query.edit_message_text(format_ml_weights(_get_ml_weights()), parse_mode="HTML", reply_markup=build_ml_menu_keyboard())
                return
            if action == "sector":
                discovery = app_services.get("discovery_service")
                rows = await discovery.get_candidate_rows("market", force_refresh=False)
                symbols = [row["symbol"] for row in rows[:25]]
                await query.edit_message_text(format_sector_status(sector_analyzer.summarize(symbols)), parse_mode="HTML", reply_markup=build_ml_menu_keyboard())
                return
            if action == "flow":
                await query.edit_message_text(format_flow_status(flow_analyzer.summarize(_get_options_flow_rows())), parse_mode="HTML", reply_markup=build_ml_menu_keyboard())
                return
            if action == "iv":
                await query.edit_message_text(format_iv_status(iv_analyzer.summarize_chain(_get_option_chain_rows())), parse_mode="HTML", reply_markup=build_ml_menu_keyboard())
                return

        if data.startswith("fprofile|"):
            profile = data.split("|", 1)[1].lower()
            config_service.set_active_filter_profile(profile)
            filters_snapshot = config_service.resolve_filters(profile=profile)
            await query.edit_message_text(f"Preset Menu → {profile.title()}", reply_markup=build_filter_categories_keyboard(filters_snapshot, profile))
            return

        if data.startswith("fcat|"):
            _, profile, category = data.split("|", 2)
            category = category.lower()
            if category not in VALID_FILTER_CATEGORIES:
                await query.answer("Invalid filter category.", show_alert=True)
                return
            values = config_service.get_filter_fields(category, profile=profile)
            context.user_data.pop("pending_filter_edit", None)
            await query.edit_message_text(_format_filter_category(profile, category, values), reply_markup=build_filter_fields_keyboard(profile, category, values))
            return

        if data.startswith("fedit|"):
            _, profile, category, field = data.split("|", 3)
            category = category.lower()
            if category not in VALID_FILTER_CATEGORIES:
                await query.answer("Invalid filter category.", show_alert=True)
                return
            current_value = config_service.get_filter_value(category, field, profile=profile)
            context.user_data["pending_filter_edit"] = {"profile": profile, "category": category, "field": field}
            await query.message.reply_text(f"Send new value for {profile}.{category}.{field}\nCurrent: {current_value}\nUse /cancel to stop.")
            return

        if data == "freset|all":
            config_service.reset_all_filter_overrides()
            context.user_data.pop("pending_filter_edit", None)
            await query.edit_message_text("All filter overrides cleared.", reply_markup=build_filter_profile_menu_keyboard(config_service.get_profile_preset_map(), config_service.get_active_filter_profile()))
            return

        if data.startswith("freset_profile|"):
            profile = data.split("|", 1)[1].lower()
            config_service.reset_filter_overrides(profile=profile)
            await query.edit_message_text(f"Reset all filter overrides for {profile}.", reply_markup=build_filter_profile_menu_keyboard(config_service.get_profile_preset_map(), profile))
            return

        if data.startswith("freset|"):
            _, profile, category = data.split("|", 2)
            category = category.lower()
            if category not in VALID_FILTER_CATEGORIES:
                await query.answer("Invalid filter category.", show_alert=True)
                return
            config_service.reset_filter_overrides(category=category, profile=profile)
            values = config_service.get_filter_fields(category, profile=profile)
            context.user_data.pop("pending_filter_edit", None)
            await query.edit_message_text(f"Reset {profile}.{category} overrides.", reply_markup=build_filter_fields_keyboard(profile, category, values))
            return

        if data.startswith("set|preset|"):
            preset_name = data.split("|", 2)[2]
            config_service.set_active_preset(preset_name)
            await query.edit_message_text(f"Overall preset updated to: {preset_name}", reply_markup=build_control_panel_keyboard())
            return

        if data.startswith("set|mode|"):
            mode = data.split("|", 2)[2]
            config_service.set_execution_mode(mode)
            await query.edit_message_text(f"Execution mode updated to: {mode}", reply_markup=build_control_panel_keyboard())
            return

        if data.startswith("toggle|strategy|"):
            strategy_name = data.split("|", 2)[2]
            states = config_service.get_strategy_states()
            current = bool(states.get(strategy_name, True))
            config_service.settings_repo.set_strategy_state(strategy_name, not current)
            await query.edit_message_text("Strategies updated", reply_markup=build_strategies_keyboard(config_service.get_strategy_states()))
            return

        await query.edit_message_text("Unknown control panel action.", reply_markup=build_control_panel_keyboard())

    return [
        CommandHandler("start", start_command),
        CommandHandler("panel", panel_command),
        CommandHandler("scans", scans_command),
        CommandHandler("scan_menu", scans_command),
        CommandHandler("config", _config),
        CommandHandler("status", _config),
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
        CommandHandler("cancel", cancel_command),
        MessageHandler(filters.TEXT & ~filters.COMMAND, _pending_text),
        CallbackQueryHandler(_guarded_callback),
    ]
