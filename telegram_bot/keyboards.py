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
        [
            [
                InlineKeyboardButton("✅ Approve", callback_data=f"a|{trade_id}"),
                InlineKeyboardButton("📝 Paper", callback_data=f"p|{trade_id}"),
                InlineKeyboardButton("❌ Reject", callback_data=f"r|{trade_id}"),
            ]
        ]
    )


def build_control_panel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Presets", callback_data="cp|presets"),
                InlineKeyboardButton("Mode", callback_data="cp|mode"),
            ],
            [
                InlineKeyboardButton("Strategies", callback_data="cp|strategies"),
                InlineKeyboardButton("Filters", callback_data="cp|filters"),
            ],
        ]
    )


def build_presets_keyboard(presets: list[str], current: str) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(f"{'✅ ' if name == current else ''}{_pretty_name(name)}", callback_data=f"set|preset|{name}")]
        for name in presets
    ]
    rows.append([InlineKeyboardButton("⬅ Back", callback_data="cp|back")])
    return InlineKeyboardMarkup(rows)


def build_mode_keyboard(current: str) -> InlineKeyboardMarkup:
    modes = [("alerts_only", "Alerts Only"), ("paper", "Paper"), ("live", "Live")]
    rows = [
        [InlineKeyboardButton(f"{'✅ ' if value == current else ''}{label}", callback_data=f"set|mode|{value}")]
        for value, label in modes
    ]
    rows.append([InlineKeyboardButton("⬅ Back", callback_data="cp|back")])
    return InlineKeyboardMarkup(rows)


def build_strategies_keyboard(states: dict[str, bool]) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(f"{'🟢' if is_enabled else '⚪'} {strategy_name}", callback_data=f"toggle|strategy|{strategy_name}")]
        for strategy_name, is_enabled in states.items()
    ]
    rows.append([InlineKeyboardButton("⬅ Back", callback_data="cp|back")])
    return InlineKeyboardMarkup(rows)


def build_filter_profile_menu_keyboard(profile_preset_map: dict[str, str], active_profile: str) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                f"{'✅ ' if profile == active_profile else ''}{_pretty_name(profile)} ({_pretty_name(profile_preset_map.get(profile, ''))})",
                callback_data=f"fprofile|{profile}",
            )
        ]
        for profile in FILTER_PROFILES
    ]
    rows.append([InlineKeyboardButton("♻ Reset All Filters", callback_data="freset|all")])
    rows.append([InlineKeyboardButton("⬅ Back", callback_data="cp|back")])
    return InlineKeyboardMarkup(rows)


def build_filter_categories_keyboard(filters_snapshot: dict[str, dict], current_profile: str) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(f"{_pretty_name(category)} ({len(filters_snapshot.get(category, {}))})", callback_data=f"fcat|{current_profile}|{category}")]
        for category in VALID_FILTER_CATEGORIES
    ]
    rows.append([InlineKeyboardButton("♻ Reset This Preset", callback_data=f"freset_profile|{current_profile}")])
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
