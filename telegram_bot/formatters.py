from __future__ import annotations

from html import escape
from typing import Any, Iterable, Mapping


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def format_trade_alert(payload: dict) -> str:
    symbol = escape(str(payload.get("symbol", "UNKNOWN")))
    strategy = escape(str(payload.get("strategy", "Unknown")))
    side = str(payload.get("side", "LONG")).upper()
    direction = "🟢 LONG" if side == "LONG" else "🔴 SHORT"
    horizon = escape(str(payload.get("trade_horizon", "DAY_TRADE")))
    regime = escape(str(payload.get("regime", "UNKNOWN")))
    entry = _to_float(payload.get("entry_price"))
    stop_loss = _to_float(payload.get("stop_loss"))
    take_profit = _to_float(payload.get("take_profit"))
    rr_ratio = _to_float(payload.get("rr_ratio"))
    confidence = int(payload.get("confidence", 0) or 0)
    benchmark = escape(str(payload.get("benchmark", "N/A")))
    trade_id = escape(str(payload.get("trade_id", "")))
    entry_zone = payload.get("entry_zone", [])
    targets = payload.get("targets", [])
    metrics = payload.get("metrics", {})
    reasons = payload.get("trigger_reasons", [])
    news_count = int(payload.get("news_count", 0) or 0)
    catalyst_headlines = payload.get("catalyst_headlines", [])[:3]

    entry_zone_text = " / ".join(f"${_to_float(v):.2f}" for v in entry_zone) if entry_zone else "N/A"
    targets_text = " | ".join(f"${_to_float(v):.2f}" for v in targets) if targets else f"${take_profit:.2f}"
    volume_ratio = _to_float(metrics.get("volume_ratio"))
    atr_pct = _to_float(metrics.get("atr_pct"))
    adx_val = _to_float(metrics.get("adx_14"))

    reason_lines = "\n".join(f"• {escape(str(item))}" for item in reasons[:5]) if reasons else "• Criteria cluster passed"
    catalyst_lines = "\n".join(f"• {escape(str(item))}" for item in catalyst_headlines) if catalyst_headlines else "• No fresh ticker-specific headlines loaded"

    return (
        f"🚨 <b>{symbol} | {strategy}</b>\n"
        f"<b>Trade ID:</b> {trade_id}\n"
        f"<b>Direction:</b> {direction}\n"
        f"<b>Regime:</b> {regime}\n"
        f"<b>Horizon:</b> {horizon}\n"
        f"<b>Benchmark:</b> {benchmark}\n"
        f"<b>Confidence:</b> {confidence}/100\n"
        f"<b>Ticker News:</b> {news_count}\n\n"
        f"<b>Entry:</b> ${entry:.2f}\n"
        f"<b>Entry Zone:</b> {entry_zone_text}\n"
        f"<b>Stop:</b> ${stop_loss:.2f}\n"
        f"<b>Primary Target:</b> ${take_profit:.2f}\n"
        f"<b>Targets:</b> {targets_text}\n"
        f"<b>R:R:</b> 1:{rr_ratio:.2f}\n\n"
        f"<b>Volume Ratio:</b> {volume_ratio:.2f}x\n"
        f"<b>ATR %:</b> {atr_pct:.2f}%\n"
        f"<b>ADX:</b> {adx_val:.2f}\n\n"
        f"<b>Why it triggered</b>\n{reason_lines}\n\n"
        f"<b>Catalyst Headlines</b>\n{catalyst_lines}\n\n"
        f"<i>Approve, paper, or reject the setup.</i>"
    )


def format_daily_report(title: str, sections: Mapping[str, Iterable[Any]] | Iterable[Any]) -> str:
    if isinstance(sections, Mapping):
        parts = [f"📊 <b>{escape(title)}</b>"]
        for section_name, bullets in sections.items():
            parts.append(f"\n<b>{escape(str(section_name))}</b>")
            if bullets:
                parts.extend(f"• {escape(str(item))}" for item in bullets)
            else:
                parts.append("• None")
        return "\n".join(parts)
    body = "\n".join(f"• {escape(str(item))}" for item in sections)
    return f"📊 <b>{escape(title)}</b>\n\n{body}"


def format_scan_status(stats: Mapping[str, Any]) -> str:
    if not stats:
        return "🔎 <b>Scan Status</b>\n\nNo scans have been recorded yet."

    errors = stats.get("errors", 0)
    rate_limited = stats.get("rate_limited", 0)
    error_examples = stats.get("error_examples", [])[:5]
    error_block = "\n".join(f"• {escape(str(item))}" for item in error_examples) if error_examples else "• None"

    return (
        "🔎 <b>Scan Status</b>\n\n"
        f"<b>Label:</b> {escape(str(stats.get('scan_label', 'unknown')))}\n"
        f"<b>Run Time:</b> {escape(str(stats.get('scan_timestamp_utc', 'n/a')))}\n"
        f"<b>Universe Loaded:</b> {stats.get('universe_loaded', 0)}\n"
        f"<b>Passed Universe Filters:</b> {stats.get('passed_universe_filters', stats.get('universe_loaded', 0))}\n"
        f"<b>Symbols Evaluated:</b> {stats.get('symbols_evaluated', stats.get('evaluated', 0))}\n"
        f"<b>Qualified Setups:</b> {stats.get('qualified_setups', stats.get('qualified', 0))}\n"
        f"<b>Rate Limited:</b> {rate_limited}\n"
        f"<b>Errors:</b> {errors}\n"
        f"<b>Top Symbols:</b> {escape(', '.join(stats.get('top_symbols', [])[:10]) or 'None')}\n\n"
        f"<b>Error Examples</b>\n{error_block}"
    )


def format_tomorrow_plan(plan: Iterable[Any]) -> str:
    bullets = list(plan)
    if not bullets:
        bullets = ["No clear bias yet. Stay selective and keep risk small."]
    body = "\n".join(f"• {escape(str(item))}" for item in bullets)
    return f"🧭 <b>Tomorrow Game Plan</b>\n\n{body}"
