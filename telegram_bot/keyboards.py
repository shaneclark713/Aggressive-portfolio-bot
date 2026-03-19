from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def build_trade_keyboard(trade_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton('✅ Approve', callback_data=f'a|{trade_id}'), InlineKeyboardButton('📝 Paper', callback_data=f'p|{trade_id}'), InlineKeyboardButton('❌ Reject', callback_data=f'r|{trade_id}')]])

def build_control_panel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton('Presets', callback_data='cp|presets'), InlineKeyboardButton('Mode', callback_data='cp|mode')],[InlineKeyboardButton('Strategies', callback_data='cp|strategies'), InlineKeyboardButton('Filters', callback_data='cp|filters')],[InlineKeyboardButton('Sell All Bot Positions', callback_data='cp|sell_all')]])
