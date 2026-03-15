from html import escape


def _to_float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return default


def format_trade_alert(payload: dict) -> str:
    symbol = escape(str(payload.get('symbol', 'UNKNOWN')))
    strategy = escape(str(payload.get('strategy', 'Unknown')))
    side = str(payload.get('side', 'LONG')).upper()
    direction = '🟢 LONG' if side == 'LONG' else '🔴 SHORT'
    entry = _to_float(payload.get('entry_price'))
    sl = _to_float(payload.get('stop_loss'))
    tp = _to_float(payload.get('take_profit'))
    rr = _to_float(payload.get('rr_ratio'))
    trade_id = escape(str(payload.get('trade_id', '')))
    horizon = escape(str(payload.get('trade_horizon', '')))
    return (
        f"🚨 <b>TRADE ALERT: {symbol}</b> 🚨\n"
        f"<b>Trade ID:</b> {trade_id}\n"
        f"<b>Strategy:</b> {strategy}\n"
        f"<b>Direction:</b> {direction}\n"
        f"<b>Horizon:</b> {horizon}\n\n"
        f"<b>Entry:</b> ${entry:.2f}\n"
        f"<b>Target:</b> ${tp:.2f} 🎯\n"
        f"<b>Stop:</b> ${sl:.2f} 🛡️\n"
        f"<b>R:R:</b> 1 : {rr:.2f}\n\n"
        f"<i>Awaiting command...</i>"
    )


def format_daily_report(title: str, bullets) -> str:
    body = '\n'.join(f'• {escape(str(item))}' for item in bullets)
    return f'📊 <b>{escape(title)}</b>\n\n{body}'
