from __future__ import annotations

import json
from typing import Any

from telegram.error import BadRequest
from telegram.ext import CallbackQueryHandler, CommandHandler, MessageHandler, filters

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
    build_execution_ladder_keyboard,
    build_execution_menu_keyboard,
    build_execution_risk_keyboard,
    build_execution_safeguards_keyboard,
    build_execution_trailing_keyboard,
    build_filter_categories_keyboard,
    build_filter_fields_keyboard,
    build_filter_profile_menu_keyboard,
    build_ml_menu_keyboard,
    build_mode_keyboard,
    build_options_expiry_keyboard,
    build_options_filters_keyboard,
    build_position_mode_keyboard,
    build_preset_profiles_keyboard,
    build_profile_preset_keyboard,
    build_presets_keyboard,
    build_scan_menu_keyboard,
    build_strategies_keyboard,
    build_trail_type_keyboard,
)
from .formatters import (
    format_chain_summary,
    format_execution_ladder,
    format_execution_risk_settings,
    format_execution_safeguards,
    format_execution_settings,
    format_execution_trailing,
    format_flow_status,
    format_iv_status,
    format_exit_ladder_submission,
    format_ladder_execution_result,
    format_ladder_submission,
    format_ml_weights,
    format_open_trails,
    format_options_settings,
    format_position_sync_result,
    format_triggered_exit_result,
    format_scan_status,
    format_sector_status,
    format_simple_lines,
    format_ticker_scan_result,
)

PENDING_FILTER_EDIT = "pending_filter_edit"
PENDING_EXEC_EDIT = "pending_execution_edit"
PENDING_OPTIONS_EDIT = "pending_options_edit"
PENDING_TICKER_SCAN = "pending_ticker_scan"

PERCENT_FIELDS = {
    "risk_pct",
    "max_spread_pct",
    "max_slippage_pct",
    "ladder_spacing_pct",
    "trail_value",
    "take_profit",
    "stop_loss",
}
INT_FIELDS = {"ladder_steps", "min_volume", "min_open_interest", "min_daily_volume", "max_concurrent_positions", "max_consecutive_losses", "expiry_value"}
BOOL_FIELDS = {"market_hours_only", "allow_premarket_entries", "allow_afterhours_entries"}
FLOAT_FIELDS = {"atr_multiplier", "delta_min", "delta_max", "contract_min_price", "contract_max_price"}
STR_FIELDS = {"position_mode", "trail_type", "expiry_mode", "chain_symbol", "entry_cutoff_time", "time_of_day_restrictor", "market_timezone", "premarket_start_time", "regular_market_open_time", "regular_market_close_time", "afterhours_end_time"}
EXECUTION_STYLE_FIELDS = {"day_trade", "swing_trade", "options"}
DEFAULT_EXECUTION_STYLE = "day_trade"


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


def _clean_number(raw: str) -> str:
    return raw.strip().replace(",", "")


def _parse_bool(raw: str) -> bool:
    lowered = raw.strip().lower()
    if lowered in {"true", "1", "yes", "on", "enabled"}:
        return True
    if lowered in {"false", "0", "no", "off", "disabled"}:
        return False
    raise ValueError("Expected true/false")


def _parse_decimal_or_percent(raw: str) -> float:
    text = _clean_number(raw)
    if text.endswith("%"):
        return float(text[:-1]) / 100.0
    value = float(text)
    if abs(value) > 1.0:
        return value / 100.0
    return value


def _render_scan_overview(name: str, payload: dict[str, Any]) -> str:
    if "stats" in payload:
        stats = payload.get("stats", {})
        candidates = payload.get("candidates", [])
        lines = [format_scan_status(stats), "", f"<b>{name} Top Candidates</b>"]
        if not candidates:
            lines.append("No candidates available.")
        else:
            for row in candidates[:8]:
                symbol = row.get("symbol", "N/A")
                setup = row.get("setup") or row.get("strategy") or "setup"
                side = row.get("side") or row.get("action") or "LONG"
                lines.append(f"• {symbol} | {setup} | {side}")
        return "\n".join(lines)
    if "headlines" in payload:
        lines = [f"<b>{name}</b>", "", f"<b>Headline Count:</b> {payload.get('headline_count', 0)}"]
        lines.extend(f"• {item}" for item in payload.get("headlines", []))
        return "\n".join(lines)
    if "events" in payload:
        lines = [f"<b>{name}</b>", "", f"<b>Event Count:</b> {payload.get('event_count', 0)}", f"<b>High Impact:</b> {payload.get('high_impact_count', 0)}"]
        lines.extend(f"• {item}" for item in payload.get("events", []))
        return "\n".join(lines)
    if "catalysts" in payload:
        lines = [f"<b>{name}</b>", "", f"<b>Symbols Checked:</b> {payload.get('symbols_checked', 0)}"]
        for item in payload.get("catalysts", []):
            symbol = item.get("symbol", "N/A")
            headline_count = item.get("headline_count", 0)
            top = "; ".join(item.get("headlines", [])[:2])
            lines.append(f"• {symbol} ({headline_count}): {top}")
        return "\n".join(lines)
    if isinstance(payload, dict):
        lines = [f"<b>{name}</b>"]
        for key, value in payload.items():
            lines.append(f"• {key}: {value}")
        return "\n".join(lines)
    return str(payload)


async def _safe_edit_message_text(query, text: str, **kwargs):
    try:
        return await query.edit_message_text(text, **kwargs)
    except BadRequest as exc:
        if "Message is not modified" in str(exc):
            return None
        raise


async def start_command(update, context):
    await update.message.reply_text("Bot online.")


async def panel_command(update, context):
    await update.message.reply_text("Control Panel", reply_markup=build_control_panel_keyboard())


async def cancel_command(update, context):
    for key in (PENDING_FILTER_EDIT, PENDING_EXEC_EDIT, PENDING_OPTIONS_EDIT, PENDING_TICKER_SCAN):
        context.user_data.pop(key, None)
    await update.message.reply_text("Canceled.")


def build_handlers(app_services, config_service, admin_chat_id: int):
    settings_repo = config_service.settings_repo
    sector_analyzer = SectorAnalyzer()
    flow_analyzer = OptionsFlowAnalyzer()
    iv_analyzer = IVAnalyzer()
    chain_service = OptionsChainService()
    trailing_stop_service = app_services.get("trailing_stop_service") or TrailingStopService(settings_repo)
    options_chain_ingest = app_services.get("options_chain_ingest_service") or OptionsChainIngestService(settings_repo, app_services.get("tradier_market_data_client") or app_services.get("tradier_live_client") or app_services.get("tradier_client"))
    live_execution_service = app_services.get("live_execution_service")
    broker_ladder_service = BrokerLadderService(app_services.get("execution_router"))
    position_sync_service = PositionSyncService(
        trailing_stop_service,
        alpaca_client=app_services.get("alpaca_client"),
        tradier_client=app_services.get("tradier_client"),
    )

    def _clear_pending(context) -> None:
        for key in (PENDING_FILTER_EDIT, PENDING_EXEC_EDIT, PENDING_OPTIONS_EDIT, PENDING_TICKER_SCAN):
            context.user_data.pop(key, None)

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

    def _normalize_execution_settings(raw: dict | None) -> dict:
        defaults = {
            "risk_pct": 0.01,
            "atr_multiplier": 1.0,
            "position_mode": "auto",
            "take_profit": 0.05,
            "stop_loss": 0.02,
            "max_spread_pct": 0.03,
            "min_volume": 500000,
            "max_slippage_pct": 0.02,
            "max_concurrent_positions": 3,
            "max_consecutive_losses": 3,
            "market_hours_only": True,
            "allow_premarket_entries": False,
            "allow_afterhours_entries": False,
            "entry_cutoff_time": "15:00",
            "time_of_day_restrictor": "15:00",
            "market_timezone": "America/New_York",
            "premarket_start_time": "04:00",
            "regular_market_open_time": "09:30",
            "regular_market_close_time": "16:00",
            "afterhours_end_time": "20:00",
            "ladder_steps": 3,
            "ladder_spacing_pct": 0.01,
            "trail_type": "percent",
            "trail_value": 0.02,
        }
        raw = dict(raw or {})
        if "profiles" in raw:
            profiles = raw.get("profiles") or {}
            return {
                "active_profile": raw.get("active_profile") or DEFAULT_EXECUTION_STYLE,
                "profiles": {
                    "day_trade": {**defaults, **dict(profiles.get("day_trade") or {})},
                    "swing_trade": {**defaults, **dict(profiles.get("swing_trade") or {})},
                    "options": {**defaults, "position_mode": "options", **dict(profiles.get("options") or {})},
                },
            }
        legacy = {k: raw[k] for k in raw.keys() if k in defaults}
        return {
            "active_profile": raw.get("active_profile") or DEFAULT_EXECUTION_STYLE,
            "profiles": {
                "day_trade": {**defaults, **legacy},
                "swing_trade": {**defaults, **legacy},
                "options": {**defaults, **legacy, "position_mode": "options"},
            },
        }

    def _get_execution_settings_blob() -> dict:
        return _normalize_execution_settings(_get_ui_settings("execution_settings", {}))

    def _get_active_execution_style() -> str:
        return _get_execution_settings_blob().get("active_profile", DEFAULT_EXECUTION_STYLE)

    def _set_active_execution_style(style: str) -> None:
        style = style if style in EXECUTION_STYLE_FIELDS else DEFAULT_EXECUTION_STYLE
        blob = _get_execution_settings_blob()
        blob["active_profile"] = style
        _set_ui_settings("execution_settings", blob)

    def _get_execution_settings(style: str | None = None) -> dict:
        blob = _get_execution_settings_blob()
        active = style or blob.get("active_profile", DEFAULT_EXECUTION_STYLE)
        return dict(blob["profiles"].get(active, blob["profiles"][DEFAULT_EXECUTION_STYLE]))

    def _update_execution_settings(style: str | None = None, **updates) -> dict:
        blob = _get_execution_settings_blob()
        active = style or blob.get("active_profile", DEFAULT_EXECUTION_STYLE)
        existing = dict(blob["profiles"].get(active, {}))
        existing.update(updates)
        blob["profiles"][active] = existing
        blob["active_profile"] = active
        _set_ui_settings("execution_settings", blob)
        return dict(existing)

    def _normalize_options_settings(raw: dict | None) -> dict:
        defaults = {
            "enabled": False,
            "delta_min": 0.30,
            "delta_max": 0.70,
            "min_open_interest": 1000,
            "min_daily_volume": 250,
            "contract_min_price": 0.10,
            "contract_max_price": 10.0,
            "expiry_mode": "weekly",
            "expiry_value": 1,
            "chain_symbol": "SPY",
        }
        raw = dict(raw or {})
        if "expiry_mode" not in raw:
            legacy_pref = str(raw.get("expiry_preference") or "weekly").lower()
            if legacy_pref == "nearest":
                legacy_pref = "0dte"
            raw["expiry_mode"] = legacy_pref if legacy_pref in {"0dte", "weekly", "monthly"} else "weekly"
        if "expiry_value" not in raw:
            raw["expiry_value"] = 0 if raw.get("expiry_mode") == "0dte" else 1
        merged = {**defaults, **raw}
        if merged["expiry_mode"] == "0dte":
            merged["expiry_value"] = 0
        else:
            merged["expiry_value"] = max(int(merged.get("expiry_value", 1) or 1), 1)
        return merged

    def _get_options_settings() -> dict:
        return _normalize_options_settings(_get_ui_settings("options_settings", {}))

    def _update_options_settings(**updates) -> dict:
        current = _get_options_settings()
        current.update(updates)
        current = _normalize_options_settings(current)
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

    def _parse_exec_or_options_value(field: str, raw: str):
        if field == "enabled" or field in BOOL_FIELDS:
            return _parse_bool(raw)
        if field in PERCENT_FIELDS:
            return _parse_decimal_or_percent(raw)
        if field in INT_FIELDS:
            return int(_clean_number(raw))
        if field in FLOAT_FIELDS:
            text = _clean_number(raw)
            if text.endswith("%"):
                return float(text[:-1]) / 100.0
            return float(text)
        if field == "entry_cutoff_time":
            text = raw.strip()
            parts = text.split(":")
            if len(parts) != 2:
                raise ValueError("Time must look like HH:MM")
            hour = int(parts[0])
            minute = int(parts[1])
            if hour < 0 or hour > 23 or minute < 0 or minute > 59:
                raise ValueError("Time must look like HH:MM")
            return f"{hour:02d}:{minute:02d}"
        if field == "expiry_mode":
            value = raw.strip().lower()
            if value not in {"0dte", "weekly", "monthly"}:
                raise ValueError("Expiry mode must be 0dte, weekly, or monthly")
            return value
        if field in STR_FIELDS:
            return raw.strip()
        return raw.strip()

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

    def _get_active_filter_profile_safe() -> str:
        profile = settings_repo.get("active_filter_profile", None)
        if not profile and hasattr(config_service, "get_active_filter_profile"):
            try:
                profile = config_service.get_active_filter_profile()
            except Exception:
                profile = None
        if profile not in {"overall", "premarket", "midday", "overnight", "options"}:
            profile = "overall"
        return profile

    def _set_active_filter_profile_safe(profile: str) -> str:
        profile = profile if profile in {"overall", "premarket", "midday", "overnight", "options"} else "overall"
        settings_repo.set("active_filter_profile", profile)
        if profile != "options" and hasattr(config_service, "set_active_filter_profile"):
            try:
                config_service.set_active_filter_profile(profile)
            except Exception:
                pass
        return profile

    def _get_profile_preset_map_safe() -> dict[str, str]:
        if hasattr(config_service, "get_profile_preset_map"):
            try:
                return dict(config_service.get_profile_preset_map())
            except Exception:
                pass
        return {"overall": "day_trade_momentum", "premarket": "premarket", "midday": "day_trade_momentum", "overnight": "swing_trade"}

    def _get_available_presets_safe() -> list[str]:
        if hasattr(config_service, "get_available_presets"):
            try:
                return list(config_service.get_available_presets())
            except Exception:
                pass
        return ["day_trade_momentum", "swing_trade", "premarket", "midday", "overnight"]

    def _get_profile_preset_safe(profile: str) -> str:
        if hasattr(config_service, "get_profile_preset"):
            try:
                return config_service.get_profile_preset(profile)
            except Exception:
                pass
        return _get_profile_preset_map_safe().get(profile, "day_trade_momentum")

    def _set_profile_preset_safe(profile: str, preset: str) -> None:
        _set_active_filter_profile_safe(profile)
        if hasattr(config_service, "set_profile_preset"):
            try:
                config_service.set_profile_preset(profile, preset)
                return
            except Exception:
                pass
        settings_repo.set(f"profile_preset.{profile}", preset)

    async def _show_execution_root(query):
        style = _get_active_execution_style()
        settings = _get_execution_settings(style)
        await _safe_edit_message_text(query, 
            format_execution_settings(settings, style),
            parse_mode="HTML",
            reply_markup=build_execution_menu_keyboard(style),
        )

    async def _show_execution_section(query, section: str):
        style = _get_active_execution_style()
        settings = _get_execution_settings(style)
        if section == "risk":
            text = format_execution_risk_settings(settings, style)
            markup = build_execution_risk_keyboard(settings, style)
        elif section == "safeguards":
            text = format_execution_safeguards(settings, style)
            markup = build_execution_safeguards_keyboard(settings, style)
        elif section == "ladder":
            text = format_execution_ladder(settings, style)
            markup = build_execution_ladder_keyboard(settings, style)
        else:
            text = format_execution_trailing(settings, style)
            markup = build_execution_trailing_keyboard(settings, style)
        await _safe_edit_message_text(query, text, parse_mode="HTML", reply_markup=markup)

    async def _show_presets_root(query):
        active_profile = _get_active_filter_profile_safe()
        await _safe_edit_message_text(query, 
            "Preset Profiles",
            reply_markup=build_preset_profiles_keyboard(_get_profile_preset_map_safe(), active_profile, _get_options_settings()),
        )

    async def _show_profile_detail(query, profile: str):
        profile = _set_active_filter_profile_safe(profile)
        if profile == "options":
            await _safe_edit_message_text(query, 
                "Options Profile",
                reply_markup=build_profile_preset_keyboard("options", [], "", _get_options_settings()),
            )
            return
        current = _get_profile_preset_safe(profile)
        await _safe_edit_message_text(query, 
            f"{profile.replace('_', ' ').title()} Profile",
            reply_markup=build_profile_preset_keyboard(profile, _get_available_presets_safe(), current, _get_options_settings()),
        )

    async def _show_option_filters(query):
        _set_active_filter_profile_safe("options")
        settings = _get_options_settings()
        await _safe_edit_message_text(query, 
            format_options_settings(settings),
            parse_mode="HTML",
            reply_markup=build_options_filters_keyboard(settings),
        )

    async def _show_filters_root(query):
        await _show_presets_root(query)

    async def _show_filter_profile(query, profile: str):
        profile = _set_active_filter_profile_safe(profile)
        if profile == "options":
            await _show_option_filters(query)
            return
        filters_snapshot = config_service.resolve_filters(profile=profile)
        await _safe_edit_message_text(query, 
            f"{profile.title()} Filters",
            reply_markup=build_filter_categories_keyboard(filters_snapshot, profile),
        )

    async def _show_filter_category(query, profile: str, category: str):
        values = config_service.get_filter_fields(category, profile=profile)
        await _safe_edit_message_text(query, 
            f"{profile.title()} / {category.title()} Filters",
            reply_markup=build_filter_fields_keyboard(profile, category, values),
        )

    async def _ml_weights(update, context):
        if await _authorize_update(update):
            await update.message.reply_text(format_ml_weights(_get_ml_weights()), parse_mode="HTML")

    async def _sector_status(update, context):
        if not await _authorize_update(update):
            return
        discovery = app_services.get("discovery_service")
        rows = await discovery.get_candidate_rows("market", force_refresh=False) if discovery else []
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
        await update.message.reply_text(
            format_chain_summary(payload["summary"]) + f"\n\n<b>Symbol:</b> {symbol}",
            parse_mode="HTML",
        )

    async def _chain_status(update, context):
        if await _authorize_update(update):
            await update.message.reply_text(format_chain_summary(chain_service.summarize_chain(_get_option_chain_rows())), parse_mode="HTML")

    async def _trail_status(update, context):
        if await _authorize_update(update):
            await update.message.reply_text(format_open_trails(trailing_stop_service.list_positions()), parse_mode="HTML")

    async def _sync_positions(update, context):
        if not await _authorize_update(update):
            return
        rows = await position_sync_service.sync_live_positions(include_demo_fallback=True)
        await update.message.reply_text(format_position_sync_result(rows), parse_mode="HTML")

    async def _scan_ticker(update, context):
        if not await _authorize_update(update):
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


    async def _submit_ladder(update, context):
        if not await _authorize_update(update):
            return
        if live_execution_service is None:
            await update.message.reply_text("Live execution service not configured.")
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
        if live_execution_service is None:
            await update.message.reply_text("Live execution service not configured.")
            return
        if len(context.args) < 5:
            await update.message.reply_text("Usage: /execute_ladder <symbol> <side> <total_size> <entry_price> <strategy> [mode]")
            return
        symbol, side, total_size, entry_price, strategy = context.args[:5]
        mode = context.args[5] if len(context.args) >= 6 else config_service.get_execution_mode()
        plan = await live_execution_service.submit_stock_ladder(symbol.upper(), side.upper(), int(total_size), float(entry_price), mode, strategy)
        if not plan.get("submit_ready", False):
            await update.message.reply_text(f"Execution blocked: {plan.get('blocked_reason') or 'not submit ready'}", parse_mode="HTML")
            return
        result = await broker_ladder_service.submit_stock_ladder(symbol.upper(), side.upper(), plan["entries"])
        await update.message.reply_text(format_ladder_execution_result(result), parse_mode="HTML")

    async def _submit_exit_ladder(update, context):
        if not await _authorize_update(update):
            return
        if live_execution_service is None:
            await update.message.reply_text("Live execution service not configured.")
            return
        if len(context.args) < 6:
            await update.message.reply_text("Usage: /submit_exit_ladder <symbol> <side> <total_size> <entry_price> <stop_loss> <strategy> [mode] [rr_targets_csv]")
            return
        symbol, side, total_size, entry_price, stop_loss, strategy = context.args[:6]
        mode = context.args[6] if len(context.args) >= 7 else config_service.get_execution_mode()
        rr_targets = [float(x) for x in context.args[7].split(',')] if len(context.args) >= 8 else None
        plan = await live_execution_service.submit_exit_ladder(symbol.upper(), side.upper(), int(total_size), float(entry_price), float(stop_loss), mode, strategy, rr_targets=rr_targets)
        await update.message.reply_text(format_exit_ladder_submission(plan), parse_mode="HTML")

    async def _execute_exit_ladder(update, context):
        if not await _authorize_update(update):
            return
        if live_execution_service is None:
            await update.message.reply_text("Live execution service not configured.")
            return
        if len(context.args) < 6:
            await update.message.reply_text("Usage: /execute_exit_ladder <symbol> <side> <total_size> <entry_price> <stop_loss> <strategy> [mode] [rr_targets_csv]")
            return
        symbol, side, total_size, entry_price, stop_loss, strategy = context.args[:6]
        mode = context.args[6] if len(context.args) >= 7 else config_service.get_execution_mode()
        rr_targets = [float(x) for x in context.args[7].split(',')] if len(context.args) >= 8 else None
        plan = await live_execution_service.submit_exit_ladder(symbol.upper(), side.upper(), int(total_size), float(entry_price), float(stop_loss), mode, strategy, rr_targets=rr_targets)
        result = await broker_ladder_service.submit_exit_ladder(symbol.upper(), plan["exits"])
        await update.message.reply_text(format_ladder_execution_result(result), parse_mode="HTML")

    async def _trigger_trails(update, context):
        if not await _authorize_update(update):
            return
        if live_execution_service is None:
            await update.message.reply_text("Live execution service not configured.")
            return
        limit_buffer_pct = _parse_decimal_or_percent(context.args[0]) if context.args else 0.0
        await position_sync_service.sync_live_positions(include_demo_fallback=False)
        result = await live_execution_service.execute_triggered_trailing_exits(limit_buffer_pct=limit_buffer_pct)
        await update.message.reply_text(format_triggered_exit_result(result), parse_mode="HTML")

    async def _option_order(update, context):
        if not await _authorize_update(update):
            return
        if live_execution_service is None:
            await update.message.reply_text("Live execution service not configured.")
            return
        if len(context.args) < 4:
            await update.message.reply_text("Usage: /option_order <symbol> <option_symbol> <side> <qty> [order_type] [price]")
            return
        symbol, option_symbol, side, qty = context.args[:4]
        order_type = context.args[4] if len(context.args) >= 5 else "market"
        price = float(context.args[5]) if len(context.args) >= 6 else None
        result = await live_execution_service.submit_single_option(symbol.upper(), option_symbol.upper(), side, int(qty), order_type=order_type, price=price)
        await update.message.reply_text(format_simple_lines("Option Order Result", [str(result)]), parse_mode="HTML")

    async def _vertical_spread(update, context):
        if not await _authorize_update(update):
            return
        if live_execution_service is None:
            await update.message.reply_text("Live execution service not configured.")
            return
        if len(context.args) < 4:
            await update.message.reply_text("Usage: /vertical_spread <symbol> <long_leg> <short_leg> <qty> [debit|credit] [order_type] [price]")
            return
        symbol, long_leg, short_leg, qty = context.args[:4]
        debit = (context.args[4].lower() if len(context.args) >= 5 else "debit") != "credit"
        order_type = context.args[5] if len(context.args) >= 6 else "market"
        price = float(context.args[6]) if len(context.args) >= 7 else None
        result = await live_execution_service.submit_vertical_spread(symbol.upper(), long_leg.upper(), short_leg.upper(), int(qty), debit=debit, order_type=order_type, price=price)
        await update.message.reply_text(format_simple_lines("Vertical Spread Result", [str(result)]), parse_mode="HTML")


    async def _set_risk_pct(update, context):
        if not await _authorize_update(update):
            return
        if not context.args:
            await update.message.reply_text("Usage: /set_risk_pct [day_trade|swing_trade] <value or percent>")
            return
        args = list(context.args)
        style = _get_active_execution_style()
        if len(args) >= 2 and args[0] in EXECUTION_STYLE_FIELDS:
            style = args.pop(0)
        _set_active_execution_style(style)
        settings = _update_execution_settings(style, risk_pct=_parse_decimal_or_percent(args[0]))
        await update.message.reply_text(format_execution_risk_settings(settings, style), parse_mode="HTML")

    async def _set_atr_multiplier(update, context):
        if not await _authorize_update(update):
            return
        if not context.args:
            await update.message.reply_text("Usage: /set_atr_multiplier [day_trade|swing_trade] <value>")
            return
        args = list(context.args)
        style = _get_active_execution_style()
        if len(args) >= 2 and args[0] in EXECUTION_STYLE_FIELDS:
            style = args.pop(0)
        _set_active_execution_style(style)
        settings = _update_execution_settings(style, atr_multiplier=float(_clean_number(args[0])))
        await update.message.reply_text(format_execution_risk_settings(settings, style), parse_mode="HTML")

    async def _set_position_mode(update, context):
        if not await _authorize_update(update):
            return
        if not context.args:
            await update.message.reply_text("Usage: /set_position_mode [day_trade|swing_trade] <auto|stock|options>")
            return
        args = list(context.args)
        style = _get_active_execution_style()
        if len(args) >= 2 and args[0] in EXECUTION_STYLE_FIELDS:
            style = args.pop(0)
        _set_active_execution_style(style)
        settings = _update_execution_settings(style, position_mode=args[0].strip().lower())
        await update.message.reply_text(format_execution_risk_settings(settings, style), parse_mode="HTML")

    async def _options_on(update, context):
        if not await _authorize_update(update):
            return
        if not context.args:
            await update.message.reply_text("Usage: /options_on <true|false>")
            return
        settings = _update_options_settings(enabled=_parse_bool(context.args[0]))
        await update.message.reply_text(format_options_settings(settings), parse_mode="HTML")

    async def _set_delta_range(update, context):
        if not await _authorize_update(update):
            return
        if len(context.args) < 2:
            await update.message.reply_text("Usage: /set_delta_range <min> <max>")
            return
        settings = _update_options_settings(delta_min=float(_clean_number(context.args[0])), delta_max=float(_clean_number(context.args[1])))
        await update.message.reply_text(format_options_settings(settings), parse_mode="HTML")

    async def _set_min_oi(update, context):
        if not await _authorize_update(update):
            return
        if not context.args:
            await update.message.reply_text("Usage: /set_min_oi <value>")
            return
        settings = _update_options_settings(min_open_interest=int(_clean_number(context.args[0])))
        await update.message.reply_text(format_options_settings(settings), parse_mode="HTML")

    async def _set_expiry(update, context):
        if not await _authorize_update(update):
            return
        if not context.args:
            await update.message.reply_text("Usage: /set_expiry <0dte|weekly|monthly> [value]")
            return
        mode = context.args[0].strip().lower()
        if mode not in {"0dte", "weekly", "monthly"}:
            await update.message.reply_text("Expiry must be 0dte, weekly, or monthly")
            return
        value = 0 if mode == "0dte" else int(_clean_number(context.args[1])) if len(context.args) >= 2 else 1
        settings = _update_options_settings(expiry_mode=mode, expiry_value=value)
        await update.message.reply_text(format_options_settings(settings), parse_mode="HTML")

    async def _set_ml_weight(update, context):
        if not await _authorize_update(update):
            return
        if len(context.args) != 2:
            await update.message.reply_text("Usage: /set_ml_weight <name> <value>")
            return
        weights = _get_ml_weights()
        weights[context.args[0]] = float(_clean_number(context.args[1]))
        _set_ml_weights(weights)
        await update.message.reply_text(format_ml_weights(weights), parse_mode="HTML")

    async def _pending_text(update, context):
        if update.effective_chat.id != admin_chat_id:
            return

        pending_ticker = context.user_data.pop(PENDING_TICKER_SCAN, None)
        if pending_ticker:
            scanner = app_services.get("scanner")
            if scanner is None:
                await update.message.reply_text("Scanner service not configured.")
                return
            parts = (update.message.text or "").strip().split()
            if not parts:
                await update.message.reply_text("Send a ticker symbol, for example: AAPL or TSLA catalyst.")
                return
            symbol = parts[0].upper()
            scan_type = parts[1].lower() if len(parts) >= 2 else pending_ticker.get("scan_type", "market")
            payload = await scanner.scan_ticker_overview(symbol, scan_type=scan_type)
            await update.message.reply_text(format_ticker_scan_result(payload), parse_mode="HTML")
            return

        pending = context.user_data.pop(PENDING_FILTER_EDIT, None)
        if pending:
            profile = pending["profile"]
            category = pending["category"]
            field = pending["field"]
            try:
                config_service.set_filter_value(category, field, update.message.text or "", profile=profile)
                values = config_service.get_filter_fields(category, profile=profile)
                await update.message.reply_text(
                    f"Saved {profile}.{category}.{field}.",
                    reply_markup=build_filter_fields_keyboard(profile, category, values),
                )
            except Exception as exc:
                context.user_data[PENDING_FILTER_EDIT] = pending
                await update.message.reply_text(f"Could not save filter value: {exc}")
            return

        pending = context.user_data.pop(PENDING_EXEC_EDIT, None)
        if pending:
            field = pending["field"]
            section = pending["section"]
            style = pending.get("style") or _get_active_execution_style()
            try:
                value = _parse_exec_or_options_value(field, update.message.text or "")
                settings = _update_execution_settings(style, **{field: value})
                if section == "risk":
                    await update.message.reply_text(format_execution_risk_settings(settings, style), parse_mode="HTML", reply_markup=build_execution_risk_keyboard(settings, style))
                elif section == "safeguards":
                    await update.message.reply_text(format_execution_safeguards(settings, style), parse_mode="HTML", reply_markup=build_execution_safeguards_keyboard(settings, style))
                elif section == "ladder":
                    await update.message.reply_text(format_execution_ladder(settings, style), parse_mode="HTML", reply_markup=build_execution_ladder_keyboard(settings, style))
                else:
                    await update.message.reply_text(format_execution_trailing(settings, style), parse_mode="HTML", reply_markup=build_execution_trailing_keyboard(settings, style))
            except Exception as exc:
                context.user_data[PENDING_EXEC_EDIT] = pending
                await update.message.reply_text(f"Could not save execution value: {exc}")
            return

        pending = context.user_data.pop(PENDING_OPTIONS_EDIT, None)
        if pending:
            field = pending["field"]
            try:
                value = _parse_exec_or_options_value(field, update.message.text or "")
                if field == "expiry_mode" and value == "0dte":
                    settings = _update_options_settings(expiry_mode=value, expiry_value=0)
                else:
                    settings = _update_options_settings(**{field: value})
                await update.message.reply_text(format_options_settings(settings), parse_mode="HTML", reply_markup=build_options_filters_keyboard(settings))
            except Exception as exc:
                context.user_data[PENDING_OPTIONS_EDIT] = pending
                await update.message.reply_text(f"Could not save options value: {exc}")
            return


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

        # panel roots
        if data == "cp|back":
            _clear_pending(context)
            await _safe_edit_message_text(query, "Control Panel", reply_markup=build_control_panel_keyboard())
            return
        if data == "cp|scan_menu":
            _clear_pending(context)
            await _safe_edit_message_text(query, "Scan Menu", reply_markup=build_scan_menu_keyboard())
            return
        if data == "cp|presets":
            _clear_pending(context)
            await _show_presets_root(query)
            return
        if data == "cp|mode":
            _clear_pending(context)
            await _safe_edit_message_text(query, "Execution Mode", reply_markup=build_mode_keyboard(config_service.get_execution_mode()))
            return
        if data == "cp|strategies":
            _clear_pending(context)
            await _safe_edit_message_text(query, "Strategies", reply_markup=build_strategies_keyboard(config_service.get_strategy_states()))
            return
        if data == "cp|filters":
            _clear_pending(context)
            await _show_filters_root(query)
            return
        if data == "cp|execution_menu":
            _clear_pending(context)
            await _show_execution_root(query)
            return
        if data == "cp|ml_menu":
            _clear_pending(context)
            await _safe_edit_message_text(query, "ML / Analytics Menu", reply_markup=build_ml_menu_keyboard())
            return

        # scan actions
        if data.startswith("scan|"):
            scanner = app_services.get("scanner")
            discovery = app_services.get("discovery_service")
            action = data.split("|", 1)[1]
            if action == "ticker_prompt":
                _clear_pending(context)
                context.user_data[PENDING_TICKER_SCAN] = {"scan_type": "market"}
                await query.message.reply_text("Send ticker symbol to scan. Examples: AAPL, NVDA premarket, TSLA catalyst. Use /cancel to stop.")
                return
            if action == "status":
                stats = scanner.get_last_scan_stats() if scanner else {}
                await _safe_edit_message_text(query, format_scan_status(stats), parse_mode="HTML", reply_markup=build_scan_menu_keyboard())
                return
            if action == "passers":
                rows = await discovery.get_passing_symbols("market", force_refresh=False) if discovery else []
                await _safe_edit_message_text(query, format_simple_lines("Passing Symbols", rows[:20] or ["No symbols available."]), parse_mode="HTML", reply_markup=build_scan_menu_keyboard())
                return
            if action == "refresh_snapshot":
                if discovery is None:
                    await _safe_edit_message_text(query, "Discovery service not configured.", reply_markup=build_scan_menu_keyboard())
                    return
                profile = _get_active_filter_profile_safe()
                snapshot = await discovery.get_snapshot(profile, force_refresh=True)
                await _safe_edit_message_text(query, 
                    format_simple_lines("Snapshot Refreshed", [f"Profile: {profile}", f"Rows: {snapshot.get('row_count', len(snapshot.get('rows', [])))}"]),
                    parse_mode="HTML",
                    reply_markup=build_scan_menu_keyboard(),
                )
                return
            if action == "snapshot_status":
                if discovery is None:
                    await _safe_edit_message_text(query, "Discovery service not configured.", reply_markup=build_scan_menu_keyboard())
                    return
                profile = _get_active_filter_profile_safe()
                status = await discovery.snapshot_status(profile)
                lines = [f"Profile: {status.get('profile')}", f"Rows: {status.get('row_count', 0)}", f"Source: {status.get('source', 'unknown')}", f"Created: {status.get('created_at', 'unknown')}"]
                await _safe_edit_message_text(query, format_simple_lines("Snapshot Status", lines), parse_mode="HTML", reply_markup=build_scan_menu_keyboard())
                return
            if scanner is None:
                await _safe_edit_message_text(query, "Scanner service not configured.", reply_markup=build_scan_menu_keyboard())
                return
            mapping = {
                "market": (scanner.scan_market_overview, "Market Scan"),
                "premarket": (scanner.scan_premarket_overview, "Premarket Scan"),
                "midday": (scanner.scan_midday_overview, "Midday Scan"),
                "overnight": (scanner.scan_overnight_overview, "Overnight Scan"),
                "news": (scanner.scan_news_overview, "News Scan"),
                "events": (scanner.scan_events_overview, "Events Scan"),
                "catalyst": (scanner.scan_catalyst_overview, "Catalyst Scan"),
                "full": (scanner.scan_full_overview, "Full Scan"),
            }
            if action in mapping:
                func, title = mapping[action]
                payload = await func()
                if action == "full":
                    lines = []
                    for name, block in payload.items():
                        if isinstance(block, dict) and "stats" in block:
                            lines.append(f"{name}: qualified={block['stats'].get('qualified', 0)} errors={block['stats'].get('errors', 0)}")
                        elif isinstance(block, dict) and "headline_count" in block:
                            lines.append(f"{name}: headlines={block.get('headline_count', 0)}")
                        elif isinstance(block, dict) and "event_count" in block:
                            lines.append(f"{name}: events={block.get('event_count', 0)}")
                        elif isinstance(block, dict) and "symbols_checked" in block:
                            lines.append(f"{name}: symbols_checked={block.get('symbols_checked', 0)}")
                    text = format_simple_lines(title, lines or ["No full scan data."])
                else:
                    text = _render_scan_overview(title, payload)
                await _safe_edit_message_text(query, text, parse_mode="HTML", reply_markup=build_scan_menu_keyboard())
                return

        # general setting callbacks
        if data.startswith("set|preset|"):
            _clear_pending(context)
            preset = data.split("|", 2)[2]
            profile = _get_active_filter_profile_safe()
            if profile == "options":
                await _show_profile_detail(query, "options")
                return
            _set_profile_preset_safe(profile, preset)
            await _show_profile_detail(query, profile)
            return
        if data.startswith("set|mode|"):
            _clear_pending(context)
            mode = data.split("|", 2)[2]
            config_service.set_execution_mode(mode)
            await _safe_edit_message_text(query, "Execution Mode", reply_markup=build_mode_keyboard(config_service.get_execution_mode()))
            return
        if data.startswith("toggle|strategy|"):
            _clear_pending(context)
            strategy_name = data.split("|", 2)[2]
            current = config_service.get_strategy_states().get(strategy_name, True)
            settings_repo.set_strategy_state(strategy_name, not current)
            await _safe_edit_message_text(query, "Strategies", reply_markup=build_strategies_keyboard(config_service.get_strategy_states()))
            return

        # combined preset/profile/filter menu
        if data.startswith("presetprofile|"):
            _clear_pending(context)
            profile = data.split("|", 1)[1]
            await _show_profile_detail(query, profile)
            return
        if data.startswith("profilefilters|"):
            _clear_pending(context)
            profile = data.split("|", 1)[1]
            await _show_filter_profile(query, profile)
            return

        # filters
        if data.startswith("fprofile|"):
            _clear_pending(context)
            profile = data.split("|", 1)[1]
            await _show_filter_profile(query, profile)
            return
        if data.startswith("fcat|"):
            _clear_pending(context)
            _, profile, category = data.split("|", 2)
            await _show_filter_category(query, profile, category)
            return
        if data.startswith("fedit|"):
            _clear_pending(context)
            _, profile, category, field = data.split("|", 3)
            context.user_data[PENDING_FILTER_EDIT] = {"profile": profile, "category": category, "field": field}
            await query.message.reply_text(f"Send new value for {profile}.{category}.{field}\nUse /cancel to stop.")
            return
        if data == "freset|all":
            _clear_pending(context)
            config_service.reset_all_filter_overrides()
            await _show_presets_root(query)
            return
        if data.startswith("freset_profile|"):
            _clear_pending(context)
            profile = data.split("|", 1)[1]
            if profile != "options":
                config_service.reset_filter_overrides(profile=profile)
            await _show_profile_detail(query, profile)
            return
        if data.startswith("freset|"):
            _clear_pending(context)
            _, profile, category = data.split("|", 2)
            config_service.reset_filter_category(category, profile=profile)
            await _show_filter_category(query, profile, category)
            return

        if data == "foptions|show":
            _clear_pending(context)
            await _show_option_filters(query)
            return
        if data.startswith("foptedit|"):
            _clear_pending(context)
            field = data.split("|", 1)[1]
            context.user_data[PENDING_OPTIONS_EDIT] = {"field": field}
            await query.message.reply_text(f"Send new value for options.{field}\nUse /cancel to stop.")
            return
        if data == "foptchoice|expiry_mode":
            _clear_pending(context)
            await _safe_edit_message_text(query, "Select expiry mode", reply_markup=build_options_expiry_keyboard(_get_options_settings().get("expiry_mode", "weekly")))
            return
        if data.startswith("foptset|expiry_mode|"):
            _clear_pending(context)
            value = data.split("|", 2)[2]
            settings = _update_options_settings(expiry_mode=value, expiry_value=0 if value == "0dte" else max(int(_get_options_settings().get("expiry_value", 1) or 1), 1))
            await _safe_edit_message_text(query, format_options_settings(settings), parse_mode="HTML", reply_markup=build_options_filters_keyboard(settings))
            return

        # execution sections
        if data.startswith("execprof|"):
            _clear_pending(context)
            style = data.split("|", 1)[1]
            _set_active_execution_style(style)
            await _show_execution_root(query)
            return
        if data in {"exec|show", "exec|risk", "exec|safeguards", "exec|ladder", "exec|trailing"}:
            _clear_pending(context)
            section = data.split("|", 1)[1]
            if section == "show":
                section = "risk"
            await _show_execution_section(query, section)
            return
        if data.startswith("execedit|"):
            _clear_pending(context)
            _, section, field = data.split("|", 2)
            context.user_data[PENDING_EXEC_EDIT] = {"section": section, "field": field, "style": _get_active_execution_style()}
            await query.message.reply_text(f"Send new value for {_get_active_execution_style()}.{field}\nUse /cancel to stop.")
            return
        if data == "execchoice|position_mode":
            _clear_pending(context)
            await _safe_edit_message_text(query, "Select position mode", reply_markup=build_position_mode_keyboard(_get_execution_settings().get("position_mode", "auto")))
            return
        if data == "execchoice|trail_type":
            _clear_pending(context)
            await _safe_edit_message_text(query, "Select trail type", reply_markup=build_trail_type_keyboard(_get_execution_settings().get("trail_type", "percent")))
            return
        if data.startswith("execset|position_mode|"):
            _clear_pending(context)
            value = data.split("|", 2)[2]
            _update_execution_settings(_get_active_execution_style(), position_mode=value)
            await _show_execution_section(query, "risk")
            return
        if data.startswith("execset|trail_type|"):
            _clear_pending(context)
            value = data.split("|", 2)[2]
            _update_execution_settings(_get_active_execution_style(), trail_type=value)
            await _show_execution_section(query, "trailing")
            return
        if data == "exec|submit_ladder":
            _clear_pending(context)
            if live_execution_service is None:
                await _safe_edit_message_text(query, "Live execution service not configured.", reply_markup=build_execution_menu_keyboard(_get_active_execution_style()))
                return
            plan = await live_execution_service.submit_stock_ladder("SPY", "LONG", 120, 10.0, config_service.get_execution_mode(), "breakout_box", trade_style=_get_active_execution_style())
            await _safe_edit_message_text(query, format_ladder_submission(plan), parse_mode="HTML", reply_markup=build_execution_menu_keyboard(_get_active_execution_style()))
            return
        if data == "exec|open_trails":
            _clear_pending(context)
            await _safe_edit_message_text(query, format_open_trails(trailing_stop_service.list_positions()), parse_mode="HTML", reply_markup=build_execution_menu_keyboard(_get_active_execution_style()))
            return

        # preset / options utilities
        if data.startswith("preset|"):
            action = data.split("|", 1)[1]
            settings = _get_options_settings()
            if action == "options_toggle":
                _clear_pending(context)
                _update_options_settings(enabled=not settings.get("enabled", False))
                await _show_profile_detail(query, "options")
                return
            if action == "chain":
                _clear_pending(context)
                await _safe_edit_message_text(query, format_chain_summary(chain_service.summarize_chain(_get_option_chain_rows())), parse_mode="HTML", reply_markup=build_profile_preset_keyboard("options", [], "", _get_options_settings()))
                return
            if action == "iv":
                _clear_pending(context)
                await _safe_edit_message_text(query, format_iv_status(iv_analyzer.summarize_chain(_get_option_chain_rows())), parse_mode="HTML", reply_markup=build_profile_preset_keyboard("options", [], "", _get_options_settings()))
                return
            if action == "flow":
                _clear_pending(context)
                await _safe_edit_message_text(query, format_flow_status(flow_analyzer.summarize(_get_options_flow_rows())), parse_mode="HTML", reply_markup=build_profile_preset_keyboard("options", [], "", _get_options_settings()))
                return
            if action == "refresh_chain":
                _clear_pending(context)
                symbol = settings.get("chain_symbol", "SPY")
                if app_services.get("tradier_client") is None:
                    await _safe_edit_message_text(query, "Tradier client not configured.", reply_markup=build_profile_preset_keyboard("options", [], "", settings))
                    return
                payload = await options_chain_ingest.refresh_chain(symbol)
                await _safe_edit_message_text(query, format_chain_summary(payload["summary"]), parse_mode="HTML", reply_markup=build_profile_preset_keyboard("options", [], "", _get_options_settings()))
                return
            if action == "edit_chain_symbol":
                _clear_pending(context)
                context.user_data[PENDING_OPTIONS_EDIT] = {"field": "chain_symbol"}
                await query.message.reply_text("Send new value for options.chain_symbol\nUse /cancel to stop.")
                return

        # ml callbacks
        # ml callbacks
        if data == "ml|show":
            _clear_pending(context)
            await _safe_edit_message_text(query, format_ml_weights(_get_ml_weights()), parse_mode="HTML", reply_markup=build_ml_menu_keyboard())
            return
        if data == "ml|sector":
            _clear_pending(context)
            discovery = app_services.get("discovery_service")
            rows = await discovery.get_candidate_rows("market", force_refresh=False) if discovery else []
            symbols = [row["symbol"] for row in rows[:25]]
            await _safe_edit_message_text(query, format_sector_status(sector_analyzer.summarize(symbols)), parse_mode="HTML", reply_markup=build_ml_menu_keyboard())
            return
        if data == "ml|flow":
            _clear_pending(context)
            await _safe_edit_message_text(query, format_flow_status(flow_analyzer.summarize(_get_options_flow_rows())), parse_mode="HTML", reply_markup=build_ml_menu_keyboard())
            return
        if data == "ml|iv":
            _clear_pending(context)
            await _safe_edit_message_text(query, format_iv_status(iv_analyzer.summarize_chain(_get_option_chain_rows())), parse_mode="HTML", reply_markup=build_ml_menu_keyboard())
            return


        await _safe_edit_message_text(query, "Unknown control panel action.", reply_markup=build_control_panel_keyboard())

    return [
        CommandHandler("start", start_command),
        CommandHandler("panel", panel_command),
        CommandHandler("ml_weights", _ml_weights),
        CommandHandler("set_ml_weight", _set_ml_weight),
        CommandHandler("sector_status", _sector_status),
        CommandHandler("flow_alerts", _flow_alerts),
        CommandHandler("iv_status", _iv_status),
        CommandHandler("refresh_option_chain", _refresh_option_chain),
        CommandHandler("chain_status", _chain_status),
        CommandHandler("scan_ticker", _scan_ticker),
        CommandHandler("trail_status", _trail_status),
        CommandHandler("sync_positions", _sync_positions),
        CommandHandler("submit_ladder", _submit_ladder),
        CommandHandler("execute_ladder", _execute_ladder),
        CommandHandler("submit_exit_ladder", _submit_exit_ladder),
        CommandHandler("execute_exit_ladder", _execute_exit_ladder),
        CommandHandler("trigger_trails", _trigger_trails),
        CommandHandler("option_order", _option_order),
        CommandHandler("vertical_spread", _vertical_spread),
        CommandHandler("set_risk_pct", _set_risk_pct),
        CommandHandler("set_atr_multiplier", _set_atr_multiplier),
        CommandHandler("set_position_mode", _set_position_mode),
        CommandHandler("options_on", _options_on),
        CommandHandler("set_delta_range", _set_delta_range),
        CommandHandler("set_min_oi", _set_min_oi),
        CommandHandler("set_expiry", _set_expiry),
        CommandHandler("cancel", cancel_command),
        MessageHandler(filters.TEXT & ~filters.COMMAND, _pending_text),
        CallbackQueryHandler(_guarded_callback),
    ]
