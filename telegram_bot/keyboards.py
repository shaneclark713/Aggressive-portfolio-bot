from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

VALID_FILTER_CATEGORIES = ("descriptive", "fundamental", "technical")


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
                InlineKeyboardButton("Presets", callback_data="cp|presets"),
                InlineKeyboardButton("Mode", callback_data="cp|mode"),
            ],
            [
                InlineKeyboardButton("Strategies", callback_data="cp|strategies"),
                InlineKeyboardButton("Filters", callback_data="cp|filters"),
            ],
            [
                InlineKeyboardButton("Sell All Bot Positions", callback_data="cp|sell_all"),
            ],
        ]
    )


def build_presets_keyboard(presets: list[str], current: str) -> InlineKeyboardMarkup:
    rows = []
    for name in presets:
        prefix = "✅ " if name == current else ""
        rows.append([InlineKeyboardButton(f"{prefix}{_pretty_name(name)}", callback_data=f"set|preset|{name}")])
    rows.append([InlineKeyboardButton("⬅ Back", callback_data="cp|back")])
    return InlineKeyboardMarkup(rows)


def build_mode_keyboard(current: str) -> InlineKeyboardMarkup:
    modes = [
        ("alerts_only", "Alerts Only"),
        ("paper", "Paper"),
        ("live", "Live"),
    ]
    rows = []
    for value, label in modes:
        prefix = "✅ " if value == current else ""
        rows.append([InlineKeyboardButton(f"{prefix}{label}", callback_data=f"set|mode|{value}")])
    rows.append([InlineKeyboardButton("⬅ Back", callback_data="cp|back")])
    return InlineKeyboardMarkup(rows)


def build_strategies_keyboard(states: dict[str, bool]) -> InlineKeyboardMarkup:
    rows = []
    for strategy_name, is_enabled in states.items():
        icon = "🟢" if is_enabled else "⚪"
        rows.append([InlineKeyboardButton(f"{icon} {strategy_name}", callback_data=f"toggle|strategy|{strategy_name}")])
    rows.append([InlineKeyboardButton("⬅ Back", callback_data="cp|back")])
    return InlineKeyboardMarkup(rows)


def build_filter_categories_keyboard(filters_snapshot: dict[str, dict], current_preset: str) -> InlineKeyboardMarkup:
    rows = []
    for category in VALID_FILTER_CATEGORIES:
        values = filters_snapshot.get(category)
        if isinstance(values, dict):
            rows.append([InlineKeyboardButton(f"{_pretty_name(category)} ({len(values)})", callback_data=f"fcat|{category}")])
    rows.append([InlineKeyboardButton("♻ Reset All Filters", callback_data="freset|all")])
    rows.append([InlineKeyboardButton("⬅ Back", callback_data="cp|back")])
    return InlineKeyboardMarkup(rows)


def build_filter_fields_keyboard(category: str, values: dict[str, object]) -> InlineKeyboardMarkup:
    rows = []
    for field, value in values.items():
        label = f"{field}: {_display_value(value)}"
        if len(label) > 48:
            label = label[:45] + "..."
        rows.append([InlineKeyboardButton(label, callback_data=f"fedit|{category}|{field}")])
    rows.append([InlineKeyboardButton("♻ Reset Category", callback_data=f"freset|{category}")])
    rows.append([InlineKeyboardButton("⬅ Back", callback_data="cp|filters")])
    return InlineKeyboardMarkup(rows)
