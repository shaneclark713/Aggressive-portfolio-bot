from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

VALID_FILTER_CATEGORIES = ("descriptive", "fundamental", "technical")
STOCK_FILTER_PROFILES = ("overall", "premarket", "midday", "overnight")
FILTER_PROFILES = (*STOCK_FILTER_PROFILES, "options")
EXECUTION_STYLES = (("day_trade", "Day Trade"), ("swing_trade", "Swing Trade"), ("options", "Options"))


def _pretty_name(value: str) -> str:
    return value.replace("_", " ").title()


def _display_value(value) -> str:
    if isinstance(value, bool):
        return "True" if value else "False"
    return str(value)


def _truncate_label(label: str, max_len: int = 46) -> str:
    return label if len(label) <= max_len else label[: max_len - 3] + "..."


def _execution_style_rows(active_style: str) -> list[list[InlineKeyboardButton]]:
    return [[
        InlineKeyboardButton(f"{'✅ ' if active_style == value else ''}{label}", callback_data=f"execprof|{value}")
        for value, label in EXECUTION_STYLES
    ]]


def build_trade_keyboard(trade_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[
            InlineKeyboardButton("✅ Approve", callback_data=f"a|{trade_id}"),
            InlineKeyboardButton("📝 Paper", callback_data=f"p|{trade_id}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"r|{trade_id}"),
        ]]
    )


def build_control_panel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Scans", callback_data="cp|scan_menu"), InlineKeyboardButton("Presets / Filters", callback_data="cp|presets")],
            [InlineKeyboardButton("Mode", callback_data="cp|mode"), InlineKeyboardButton("Strategies", callback_data="cp|strategies")],
            [InlineKeyboardButton("Execution", callback_data="cp|execution_menu")],
            [InlineKeyboardButton("ML", callback_data="cp|ml_menu"), InlineKeyboardButton("Exec Profiles", callback_data="cp|exec_profiles")],
        ]
    )


def build_scan_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Market", callback_data="scan|market"), InlineKeyboardButton("Premarket", callback_data="scan|premarket")],
            [InlineKeyboardButton("Midday", callback_data="scan|midday"), InlineKeyboardButton("Overnight", callback_data="scan|overnight")],
            [InlineKeyboardButton("News", callback_data="scan|news"), InlineKeyboardButton("Events", callback_data="scan|events")],
            [InlineKeyboardButton("Catalyst", callback_data="scan|catalyst"), InlineKeyboardButton("Full Scan", callback_data="scan|full")],
            [InlineKeyboardButton("Scan Status", callback_data="scan|status"), InlineKeyboardButton("Passers", callback_data="scan|passers")],
            [InlineKeyboardButton("Refresh Snapshot", callback_data="scan|refresh_snapshot"), InlineKeyboardButton("Snapshot Status", callback_data="scan|snapshot_status")],
            [InlineKeyboardButton("⬅ Back", callback_data="cp|back")],
        ]
    )


def build_execution_menu_keyboard(active_style: str) -> InlineKeyboardMarkup:
    rows = _execution_style_rows(active_style)
    rows.extend(
        [
            [InlineKeyboardButton("Risk Settings", callback_data="exec|risk"), InlineKeyboardButton("Safeguards", callback_data="exec|safeguards")],
            [InlineKeyboardButton("Entry Ladder", callback_data="exec|ladder"), InlineKeyboardButton("Trailing Stop", callback_data="exec|trailing")],
            [InlineKeyboardButton("Submit Ladder", callback_data="exec|submit_ladder"), InlineKeyboardButton("Open Trails", callback_data="exec|open_trails")],
            [InlineKeyboardButton("⬅ Back", callback_data="cp|back")],
        ]
    )
    return InlineKeyboardMarkup(rows)


def build_execution_risk_keyboard(settings: dict, active_style: str) -> InlineKeyboardMarkup:
    rows = _execution_style_rows(active_style)
    rows.extend(
        [
            [InlineKeyboardButton(f"Risk %: {_display_value(settings.get('risk_pct'))}", callback_data="execedit|risk|risk_pct")],
            [InlineKeyboardButton(f"ATR Multiplier: {_display_value(settings.get('atr_multiplier'))}", callback_data="execedit|risk|atr_multiplier")],
            [InlineKeyboardButton(f"Take Profit: {_display_value(settings.get('take_profit'))}", callback_data="execedit|risk|take_profit")],
            [InlineKeyboardButton(f"Stop Loss: {_display_value(settings.get('stop_loss'))}", callback_data="execedit|risk|stop_loss")],
            [InlineKeyboardButton(f"Position Mode: {_pretty_name(str(settings.get('position_mode', 'auto')))}", callback_data="execchoice|position_mode")],
            [InlineKeyboardButton("⬅ Back", callback_data="cp|execution_menu")],
        ]
    )
    return InlineKeyboardMarkup(rows)


def build_execution_safeguards_keyboard(settings: dict, active_style: str) -> InlineKeyboardMarkup:
    rows = _execution_style_rows(active_style)
    rows.extend(
        [
            [InlineKeyboardButton(f"Max Spread %: {_display_value(settings.get('max_spread_pct'))}", callback_data="execedit|safeguards|max_spread_pct")],
            [InlineKeyboardButton(f"Min Volume: {_display_value(settings.get('min_volume'))}", callback_data="execedit|safeguards|min_volume")],
            [InlineKeyboardButton(f"Max Slippage %: {_display_value(settings.get('max_slippage_pct'))}", callback_data="execedit|safeguards|max_slippage_pct")],
            [InlineKeyboardButton(f"Max Concurrent: {_display_value(settings.get('max_concurrent_positions'))}", callback_data="execedit|safeguards|max_concurrent_positions")],
            [InlineKeyboardButton(f"Max Consecutive Losses: {_display_value(settings.get('max_consecutive_losses'))}", callback_data="execedit|safeguards|max_consecutive_losses")],
            [InlineKeyboardButton(f"Market Hours Only: {_display_value(settings.get('market_hours_only'))}", callback_data="execedit|safeguards|market_hours_only")],
            [InlineKeyboardButton(f"Allow Premarket: {_display_value(settings.get('allow_premarket_entries'))}", callback_data="execedit|safeguards|allow_premarket_entries")],
            [InlineKeyboardButton(f"Allow Afterhours: {_display_value(settings.get('allow_afterhours_entries'))}", callback_data="execedit|safeguards|allow_afterhours_entries")],
            [InlineKeyboardButton(f"Entry Cutoff: {_display_value(settings.get('entry_cutoff_time'))}", callback_data="execedit|safeguards|entry_cutoff_time")],
            [InlineKeyboardButton("⬅ Back", callback_data="cp|execution_menu")],
        ]
    )
    return InlineKeyboardMarkup(rows)


def build_execution_ladder_keyboard(settings: dict, active_style: str) -> InlineKeyboardMarkup:
    rows = _execution_style_rows(active_style)
    rows.extend(
        [
            [InlineKeyboardButton(f"Ladder Steps: {_display_value(settings.get('ladder_steps'))}", callback_data="execedit|ladder|ladder_steps")],
            [InlineKeyboardButton(f"Ladder Spacing %: {_display_value(settings.get('ladder_spacing_pct'))}", callback_data="execedit|ladder|ladder_spacing_pct")],
            [InlineKeyboardButton("Preview / Submit", callback_data="exec|submit_ladder")],
            [InlineKeyboardButton("⬅ Back", callback_data="cp|execution_menu")],
        ]
    )
    return InlineKeyboardMarkup(rows)


def build_execution_trailing_keyboard(settings: dict, active_style: str) -> InlineKeyboardMarkup:
    rows = _execution_style_rows(active_style)
    rows.extend(
        [
            [InlineKeyboardButton(f"Trail Type: {_pretty_name(str(settings.get('trail_type', 'percent')))}", callback_data="execchoice|trail_type")],
            [InlineKeyboardButton(f"Trail Value: {_display_value(settings.get('trail_value'))}", callback_data="execedit|trailing|trail_value")],
            [InlineKeyboardButton("Open Trails", callback_data="exec|open_trails")],
            [InlineKeyboardButton("⬅ Back", callback_data="cp|execution_menu")],
        ]
    )
    return InlineKeyboardMarkup(rows)


def build_position_mode_keyboard(current: str) -> InlineKeyboardMarkup:
    values = [("auto", "Auto"), ("stock", "Stock"), ("options", "Options")]
    rows = [[InlineKeyboardButton(f"{'✅ ' if current == value else ''}{label}", callback_data=f"execset|position_mode|{value}")] for value, label in values]
    rows.append([InlineKeyboardButton("⬅ Back", callback_data="exec|risk")])
    return InlineKeyboardMarkup(rows)


def build_trail_type_keyboard(current: str) -> InlineKeyboardMarkup:
    values = [("percent", "Percent"), ("atr", "ATR"), ("price", "Price")]
    rows = [[InlineKeyboardButton(f"{'✅ ' if current == value else ''}{label}", callback_data=f"execset|trail_type|{value}")] for value, label in values]
    rows.append([InlineKeyboardButton("⬅ Back", callback_data="exec|trailing")])
    return InlineKeyboardMarkup(rows)


def build_options_filters_keyboard(settings: dict) -> InlineKeyboardMarkup:
    expiry_mode = _pretty_name(str(settings.get("expiry_mode", "weekly")))
    expiry_value = settings.get("expiry_value", 1)
    rows = [
        [InlineKeyboardButton(f"Enabled: {_display_value(settings.get('enabled'))}", callback_data="foptedit|enabled")],
        [InlineKeyboardButton(f"Delta Min: {settings.get('delta_min')}", callback_data="foptedit|delta_min")],
        [InlineKeyboardButton(f"Delta Max: {settings.get('delta_max')}", callback_data="foptedit|delta_max")],
        [InlineKeyboardButton(f"Min OI: {settings.get('min_open_interest')}", callback_data="foptedit|min_open_interest")],
        [InlineKeyboardButton(f"Min Daily Volume: {settings.get('min_daily_volume')}", callback_data="foptedit|min_daily_volume")],
        [InlineKeyboardButton(f"Contract Min Price: {settings.get('contract_min_price')}", callback_data="foptedit|contract_min_price")],
        [InlineKeyboardButton(f"Contract Max Price: {settings.get('contract_max_price')}", callback_data="foptedit|contract_max_price")],
        [InlineKeyboardButton(f"Expiry Type: {expiry_mode}", callback_data="foptchoice|expiry_mode")],
        [InlineKeyboardButton(f"Expiry Value: {expiry_value}", callback_data="foptedit|expiry_value")],
        [InlineKeyboardButton(f"Chain Symbol: {settings.get('chain_symbol', 'SPY')}", callback_data="foptedit|chain_symbol")],
        [InlineKeyboardButton("⬅ Back", callback_data="presetprofile|options")],
    ]
    return InlineKeyboardMarkup(rows)


def build_options_expiry_keyboard(current: str) -> InlineKeyboardMarkup:
    values = [("0dte", "0DTE"), ("weekly", "Weekly"), ("monthly", "Monthly")]
    rows = [[InlineKeyboardButton(f"{'✅ ' if current == value else ''}{label}", callback_data=f"foptset|expiry_mode|{value}")] for value, label in values]
    rows.append([InlineKeyboardButton("⬅ Back", callback_data="foptions|show")])
    return InlineKeyboardMarkup(rows)


def build_ml_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("ML Weights", callback_data="ml|show"), InlineKeyboardButton("Sector Status", callback_data="ml|sector")],
            [InlineKeyboardButton("Flow Status", callback_data="ml|flow"), InlineKeyboardButton("IV Status", callback_data="ml|iv")],
            [InlineKeyboardButton("⬅ Back", callback_data="cp|back")],
        ]
    )


def build_execution_profile_menu_keyboard(mode: str, strategies: list[str]) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(f"{mode}: {strategy}", callback_data=f"ep|view|{mode}|{strategy}")] for strategy in strategies]
    rows.append([InlineKeyboardButton("⬅ Back", callback_data="cp|back")])
    return InlineKeyboardMarkup(rows)


def build_execution_profile_edit_keyboard(mode: str, strategy: str) -> InlineKeyboardMarkup:
    fields = [("risk_pct", "Risk %"), ("atr_multiplier", "ATR Mult"), ("ladder_steps", "Ladder Steps"), ("ladder_spacing_pct", "Ladder Spacing"), ("trail_value", "Trail Value")]
    rows = [[InlineKeyboardButton(label, callback_data=f"ep|edit|{mode}|{strategy}|{field}")] for field, label in fields]
    rows.append([InlineKeyboardButton("⬅ Back", callback_data="cp|exec_profiles")])
    return InlineKeyboardMarkup(rows)


def build_preset_profiles_keyboard(profile_preset_map: dict[str, str], active_profile: str, options_settings: dict | None = None) -> InlineKeyboardMarkup:
    options_settings = options_settings or {}
    rows: list[list[InlineKeyboardButton]] = []
    for profile in FILTER_PROFILES:
        if profile == "options":
            enabled = "ON" if options_settings.get("enabled") else "OFF"
            label = f"Options ({enabled})"
        else:
            label = f"{_pretty_name(profile)} ({_pretty_name(profile_preset_map.get(profile, ''))})"
        rows.append([InlineKeyboardButton(f"{'✅ ' if active_profile == profile else ''}{label}", callback_data=f"presetprofile|{profile}")])
    rows.append([InlineKeyboardButton("♻ Reset All Filters", callback_data="freset|all")])
    rows.append([InlineKeyboardButton("⬅ Back", callback_data="cp|back")])
    return InlineKeyboardMarkup(rows)


def build_profile_preset_keyboard(profile: str, presets: list[str], current: str, options_settings: dict) -> InlineKeyboardMarkup:
    if profile == "options":
        enabled_text = "🟢 Options ON" if options_settings.get("enabled") else "⚪ Options OFF"
        chain_symbol = str(options_settings.get("chain_symbol", "SPY"))
        return InlineKeyboardMarkup(
            [
                [InlineKeyboardButton(enabled_text, callback_data="preset|options_toggle")],
                [InlineKeyboardButton("Filters", callback_data="profilefilters|options")],
                [InlineKeyboardButton(f"Chain Symbol: {chain_symbol}", callback_data="preset|edit_chain_symbol")],
                [InlineKeyboardButton("Chain Summary", callback_data="preset|chain"), InlineKeyboardButton("Refresh Chain", callback_data="preset|refresh_chain")],
                [InlineKeyboardButton("IV Status", callback_data="preset|iv"), InlineKeyboardButton("Flow Status", callback_data="preset|flow")],
                [InlineKeyboardButton("⬅ Profiles", callback_data="cp|presets")],
            ]
        )

    rows = [[InlineKeyboardButton(f"{'✅ ' if name == current else ''}{_pretty_name(name)}", callback_data=f"set|preset|{name}")] for name in presets]
    rows.extend(
        [
            [InlineKeyboardButton("Filters", callback_data=f"profilefilters|{profile}")],
            [InlineKeyboardButton("♻ Reset This Profile", callback_data=f"freset_profile|{profile}")],
            [InlineKeyboardButton("⬅ Profiles", callback_data="cp|presets")],
        ]
    )
    return InlineKeyboardMarkup(rows)


def build_presets_keyboard(presets: list[str], current: str, options_settings: dict) -> InlineKeyboardMarkup:
    return build_profile_preset_keyboard("overall", presets, current, options_settings)


def build_mode_keyboard(current: str) -> InlineKeyboardMarkup:
    modes = [("alerts_only", "Alerts Only"), ("paper", "Paper"), ("live", "Live")]
    rows = [[InlineKeyboardButton(f"{'✅ ' if value == current else ''}{label}", callback_data=f"set|mode|{value}")] for value, label in modes]
    rows.append([InlineKeyboardButton("⬅ Back", callback_data="cp|back")])
    return InlineKeyboardMarkup(rows)


def build_strategies_keyboard(states: dict[str, bool]) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(f"{'🟢' if is_enabled else '⚪'} {strategy_name}", callback_data=f"toggle|strategy|{strategy_name}")] for strategy_name, is_enabled in states.items()]
    rows.append([InlineKeyboardButton("⬅ Back", callback_data="cp|back")])
    return InlineKeyboardMarkup(rows)


def build_filter_profile_menu_keyboard(profile_preset_map: dict[str, str], active_profile: str) -> InlineKeyboardMarkup:
    return build_preset_profiles_keyboard(profile_preset_map, active_profile, {})


def build_filter_categories_keyboard(filters_snapshot: dict[str, dict], current_profile: str) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(f"{_pretty_name(category)} ({len(filters_snapshot.get(category, {}))})", callback_data=f"fcat|{current_profile}|{category}")] for category in VALID_FILTER_CATEGORIES]
    rows.append([InlineKeyboardButton("♻ Reset This Profile", callback_data=f"freset_profile|{current_profile}")])
    rows.append([InlineKeyboardButton("⬅ Profile", callback_data=f"presetprofile|{current_profile}")])
    return InlineKeyboardMarkup(rows)


def build_filter_fields_keyboard(profile: str, category: str, values: dict[str, object]) -> InlineKeyboardMarkup:
    rows = []
    for field, value in values.items():
        label = _truncate_label(f"{field}: {_display_value(value)}")
        rows.append([InlineKeyboardButton(label, callback_data=f"fedit|{profile}|{category}|{field}")])
    rows.append([InlineKeyboardButton("♻ Reset Category", callback_data=f"freset|{profile}|{category}")])
    rows.append([InlineKeyboardButton("⬅ Filters", callback_data=f"profilefilters|{profile}")])
    return InlineKeyboardMarkup(rows)
