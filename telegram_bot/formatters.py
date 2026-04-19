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
    direction = "🟢 LONG" if side in {"LONG", "BUY"} else "🔴 SHORT"
    horizon = escape(str(payload.get("trade_horizon", "DAY_TRADE")))
    regime = escape(str(payload.get("regime", "UNKNOWN")))
    entry = _to_float(payload.get("entry_price", payload.get("entry")))
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
    catalysts = payload.get("catalyst_headlines", [])

    entry_zone_text = " / ".join(f"${_to_float(v):.2f}" for v in entry_zone) if entry_zone else "N/A"
    targets_text = " | ".join(f"${_to_float(v):.2f}" for v in targets) if targets else f"${take_profit:.2f}"
    volume_ratio = _to_float(metrics.get("volume_ratio"))
    atr_pct = _to_float(metrics.get("atr_pct"))
    adx_val = _to_float(metrics.get("adx_14"))
    reason_lines = "\n".join(f"• {escape(str(item))}" for item in reasons[:5]) if reasons else "• Criteria cluster passed"
    catalyst_lines = "\n".join(f"• {escape(str(item))}" for item in catalysts[:3]) if catalysts else "• No fresh ticker headlines loaded"

    return (
        f"🚨 <b>{symbol} | {strategy}</b>\n"
        f"<b>Trade ID:</b> {trade_id}\n"
        f"<b>Direction:</b> {direction}\n"
        f"<b>Regime:</b> {regime}\n"
        f"<b>Horizon:</b> {horizon}\n"
        f"<b>Benchmark:</b> {benchmark}\n"
        f"<b>Confidence:</b> {confidence}/100\n\n"
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
        f"<b>Catalysts</b>\n{catalyst_lines}\n\n"
        f"<i>Approve, paper, or reject the setup.</i>"
    )


def format_daily_report(title: str, sections: Mapping[str, Iterable[Any]] | Iterable[Any]) -> str:
    if isinstance(sections, Mapping):
        parts = [f"📊 <b>{escape(title)}</b>"]
        for section_name, bullets in sections.items():
            parts.append(f"\n<b>{escape(str(section_name))}</b>")
            bullet_list = list(bullets) if bullets is not None else []
            if bullet_list:
                parts.extend(f"• {escape(str(item))}" for item in bullet_list)
            else:
                parts.append("• None")
        return "\n".join(parts)
    body = "\n".join(f"• {escape(str(item))}" for item in sections)
    return f"📊 <b>{escape(title)}</b>\n\n{body}"


def format_scan_status(stats: Mapping[str, Any]) -> str:
    if not stats:
        return "🔎 <b>Scan Status</b>\n\nNo scans have been recorded yet."
    error_examples = stats.get("error_examples", [])[:5]
    error_block = "\n".join(f"• {escape(str(item))}" for item in error_examples) if error_examples else "• None"
    return (
        "🔎 <b>Scan Status</b>\n\n"
        f"<b>Label:</b> {escape(str(stats.get('scan_label', 'unknown')))}\n"
        f"<b>Type:</b> {escape(str(stats.get('scan_type', 'unknown')))}\n"
        f"<b>Run Time:</b> {escape(str(stats.get('scan_timestamp_utc', 'n/a')))}\n"
        f"<b>Universe Loaded:</b> {stats.get('universe_loaded', 0)}\n"
        f"<b>Symbols Evaluated:</b> {stats.get('symbols_evaluated', stats.get('evaluated', 0))}\n"
        f"<b>Qualified Setups:</b> {stats.get('qualified_setups', stats.get('qualified', 0))}\n"
        f"<b>Rate Limited:</b> {stats.get('rate_limited', 0)}\n"
        f"<b>Errors:</b> {stats.get('errors', 0)}\n"
        f"<b>Top Symbols:</b> {escape(', '.join(stats.get('top_symbols', [])[:10]) or 'None')}\n\n"
        f"<b>Error Examples</b>\n{error_block}"
    )


def format_news_scan(summary: Mapping[str, Any]) -> str:
    headlines = summary.get("headlines", [])
    return format_daily_report(
        "📰 News Scan",
        {
            "Summary": [f"Headline count: {summary.get('headline_count', len(headlines))}"],
            "Top Headlines": headlines or ["None loaded"],
        },
    )


def format_event_scan(summary: Mapping[str, Any]) -> str:
    return format_daily_report(
        "📅 Event Scan",
        {
            "Summary": [
                f"Events loaded: {summary.get('event_count', 0)}",
                f"High-impact events: {summary.get('high_impact_count', 0)}",
            ],
            "Today's Events": summary.get("events", []) or ["None loaded"],
        },
    )


def format_catalyst_scan(summary: Mapping[str, Any]) -> str:
    rows = []
    for item in summary.get("catalysts", []):
        top = " | ".join(item.get("headlines", [])[:2]) or "No headlines"
        rows.append(f"{item.get('symbol', 'UNKNOWN')}: {item.get('headline_count', 0)} headline(s) | {top}")
    return format_daily_report(
        "⚡ Catalyst Scan",
        {
            "Summary": [f"Symbols checked: {summary.get('symbols_checked', 0)}"],
            "Catalysts": rows or ["No catalyst headlines loaded"],
        },
    )


def format_full_scan_summary(summary: Mapping[str, Any]) -> str:
    return format_daily_report(
        "🧩 Full Scan Summary",
        {
            "Premarket": [
                f"Candidates: {len(summary.get('premarket', {}).get('candidates', []))}",
                f"Rate limited: {summary.get('premarket', {}).get('stats', {}).get('rate_limited', 0)}",
            ],
            "Market": [
                f"Candidates: {len(summary.get('market', {}).get('candidates', []))}",
                f"Rate limited: {summary.get('market', {}).get('stats', {}).get('rate_limited', 0)}",
            ],
            "Midday": [
                f"Candidates: {len(summary.get('midday', {}).get('candidates', []))}",
                f"Rate limited: {summary.get('midday', {}).get('stats', {}).get('rate_limited', 0)}",
            ],
            "Overnight": [
                f"Candidates: {len(summary.get('overnight', {}).get('candidates', []))}",
                f"Rate limited: {summary.get('overnight', {}).get('stats', {}).get('rate_limited', 0)}",
            ],
            "News / Events / Catalyst": [
                f"News headlines: {summary.get('news', {}).get('headline_count', 0)}",
                f"Events: {summary.get('events', {}).get('event_count', 0)}",
                f"Catalyst symbols: {summary.get('catalyst', {}).get('symbols_checked', 0)}",
            ],
        },
    )


def format_tomorrow_plan(plan):
    bullets = list(plan) if plan else ["No clear bias yet. Stay selective and keep risk small."]
    return "🧭 <b>Tomorrow Game Plan</b>\n\n" + "\n".join(f"• {escape(str(item))}" for item in bullets)


def format_snapshot_status(status: Mapping[str, Any]) -> str:
    if not status:
        return "🗂 <b>Snapshot Status</b>\n\nNo snapshot has been built yet."
    return (
        "🗂 <b>Snapshot Status</b>\n\n"
        f"<b>Profile:</b> {escape(str(status.get('profile', 'unknown')))}\n"
        f"<b>Created:</b> {escape(str(status.get('created_at', 'n/a')))}\n"
        f"<b>Rows:</b> {status.get('row_count', 0)}\n"
        f"<b>Skipped:</b> {status.get('skipped', 0)}\n"
        f"<b>Source:</b> {escape(str(status.get('source', 'unknown')))}\n"
        f"<b>Reason:</b> {escape(str(status.get('refresh_reason', 'unknown')))}"
    )


def format_passers(scan_type: str, rows: Iterable[Mapping[str, Any]]) -> str:
    rows = list(rows)
    if not rows:
        return f"🌊 <b>{escape(scan_type.title())} Passers</b>\n\nNo symbols are currently passing the discovery filters."
    lines = []
    for row in rows[:25]:
        lines.append(
            f"• {escape(str(row.get('symbol', 'UNKNOWN')))} | ${_to_float(row.get('price')):.2f} | "
            f"${_to_float(row.get('day_dollar_volume')) / 1_000_000:.1f}M DV | {_to_float(row.get('change_pct')):.2f}%"
        )
    return f"🌊 <b>{escape(scan_type.title())} Passers</b>\n\n" + "\n".join(lines)
