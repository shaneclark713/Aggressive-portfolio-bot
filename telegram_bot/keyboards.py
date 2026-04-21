from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

VALID_FILTER_CATEGORIES = ("descriptive", "fundamental", "technical")
FILTER_PROFILES = ("overall", "premarket", "midday", "overnight")


def _pretty_name(value: str) -> str:
    return value.replace("_", " ").title()


def _display_value(value) -> str:
    if isinstance(value, bool):
        return "True" if value else "False"
    return str(value)


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
            [
                InlineKeyboardButton("Scans", callback_data="cp|scan_menu"),
                InlineKeyboardButton("Presets", callback_data="cp|presets"),
            ],
            [
                InlineKeyboardButton("Mode", callback_data="cp|mode"),
                InlineKeyboardButton("Strategies", callback_data="cp|strategies"),
            ],
            [
                InlineKeyboardButton("Filters", callback_data="cp|filters"),
                InlineKeyboardButton("Execution", callback_data="cp|execution_menu"),
            ],
            [
                InlineKeyboardButton("Options", callback_data="cp|options_menu"),
                InlineKeyboardButton("ML", callback_data="cp|ml_menu"),
            ],
            [InlineKeyboardButton("Exec Profiles", callback_data="cp|exec_profiles")],
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


def build_execution_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Risk Settings", callback_data="exec|show"), InlineKeyboardButton("Safeguards", callback_data="exec|safeguards")],
            [InlineKeyboardButton("Entry Ladder", callback_data="exec|ladder"), InlineKeyboardButton("Trailing Stop", callback_data="exec|trailing")],
            [InlineKeyboardButton("Submit Ladder", callback_data="exec|submit_ladder"), InlineKeyboardButton("Open Trails", callback_data="exec|open_trails")],
            [InlineKeyboardButton("⬅ Back", callback_data="cp|back")],
        ]
    )


def build_options_menu_keyboard(options_settings: dict) -> InlineKeyboardMarkup:
    enabled_text = "🟢 Options ON" if options_settings.get("enabled") else "⚪ Options OFF"
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(enabled_text, callback_data="opt|toggle")],
            [InlineKeyboardButton("Delta/OI/Expiry", callback_data="opt|show"), InlineKeyboardButton("Chain Summary", callback_data="opt|chain")],
            [InlineKeyboardButton("IV Status", callback_data="opt|iv"), InlineKeyboardButton("Flow Status", callback_data="opt|flow")],
            [InlineKeyboardButton("Refresh Chain", callback_data="opt|refresh_chain"), InlineKeyboardButton("⬅ Back", callback_data="cp|back")],
        ]
    )


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
    fields = [
        ("risk_pct", "Risk %"),
        ("atr_multiplier", "ATR Mult"),
        ("ladder_steps", "Ladder Steps"),
        ("ladder_spacing_pct", "Ladder Spacing"),
        ("trail_value", "Trail Value"),
    ]
    rows = [[InlineKeyboardButton(label, callback_data=f"ep|edit|{mode}|{strategy}|{field}")] for field, label in fields]
    rows.append([InlineKeyboardButton("⬅ Back", callback_data="cp|exec_profiles")])
    return InlineKeyboardMarkup(rows)


def build_presets_keyboard(presets: list[str], current: str) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(f"{'✅ ' if name == current else ''}{_pretty_name(name)}", callback_data=f"set|preset|{name}")] for name in presets]
    rows.append([InlineKeyboardButton("⬅ Back", callback_data="cp|back")])
    return InlineKeyboardMarkup(rows)


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
    rows = [[InlineKeyboardButton(f"{'✅ ' if profile == active_profile else ''}{_pretty_name(profile)} ({_pretty_name(profile_preset_map.get(profile, ''))})", callback_data=f"fprofile|{profile}")] for profile in FILTER_PROFILES]
    rows.append([InlineKeyboardButton("♻ Reset All Filters", callback_data="freset|all")])
    rows.append([InlineKeyboardButton("⬅ Back", callback_data="cp|back")])
    return InlineKeyboardMarkup(rows)


def build_filter_categories_keyboard(filters_snapshot: dict[str, dict], current_profile: str) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(f"{_pretty_name(category)} ({len(filters_snapshot.get(category, {}))})", callback_data=f"fcat|{current_profile}|{category}")] for category in VALID_FILTER_CATEGORIES]
    rows.append([InlineKeyboardButton("♻ Reset This Profile", callback_data=f"freset_profile|{current_profile}")])
    rows.append([InlineKeyboardButton("⬅ Back", callback_data="cp|filters")])
    return InlineKeyboardMarkup(rows)


def build_filter_fields_keyboard(profile: str, category: str, values: dict[str, object]) -> InlineKeyboardMarkup:
    rows = []
    for field, value in values.items():
        label = f"{field}: {_display_value(value)}"
        if len(label) > 48:
            label = label[:45] + "..."
        rows.append([InlineKeyboardButton(label, callback_data=f"fedit|{profile}|{category}|{field}")])
    rows.append([InlineKeyboardButton("♻ Reset Category", callback_data=f"freset|{profile}|{category}")])
    rows.append([InlineKeyboardButton("⬅ Back", callback_data=f"fprofile|{profile}")])
    return InlineKeyboardMarkup(rows)
