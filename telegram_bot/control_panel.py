from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def preset_keyboard(presets: dict) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(meta.get("label", name), callback_data=f"cpreset|{name}")] for name, meta in presets.items()]
    rows.append([InlineKeyboardButton("⬅ Back", callback_data="cp|back")])
    return InlineKeyboardMarkup(rows)


def mode_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton("Alerts Only", callback_data="cmode|alerts_only")],
        [InlineKeyboardButton("Approval Only", callback_data="cmode|approval_only")],
        [InlineKeyboardButton("Automated", callback_data="cmode|automated")],
        [InlineKeyboardButton("⬅ Back", callback_data="cp|back")],
    ]
    return InlineKeyboardMarkup(rows)
