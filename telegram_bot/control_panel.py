from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def preset_keyboard(presets:list[str]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton(name, callback_data=f'cpreset|{name}')] for name in presets])

def mode_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton('Alerts Only', callback_data='cmode|alerts_only')],[InlineKeyboardButton('Approval Only', callback_data='cmode|approval_only')],[InlineKeyboardButton('Automated', callback_data='cmode|automated')]])
