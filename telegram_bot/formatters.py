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

    entry_zone_text = " / ".join(f"${_to_float(v):.2f}" for v in entry_zone) if entry_zone else "N/A"
    targets_text = " | ".join(f"${_to_float(v):.2f}" for v in targets) if targets else f"${take_profit:.2f}"
    volume_ratio = _to_float(metrics.get("volume_ratio"))
    atr_pct = _to_float(metrics.get("atr_pct"))
    adx_val = _to_float(metrics.get("adx_14"))

    reason_lines = "
".join(f"• {escape(str(item))}" for item in reasons[:5]) if reasons else "• Criteria cluster passed"

    return (
        f"🚨 <b>{symbol} | {strategy}</b>
"
        f"<b>Trade ID:</b> {trade_id}
"
        f"<b>Direction:</b> {direction}
"
        f"<b>Regime:</b> {regime}
"
        f"<b>Horizon:</b> {horizon}
"
        f"<b>Benchmark:</b> {benchmark}
"
        f"<b>Confidence:</b> {confidence}/100

"
        f"<b>Entry:</b> ${entry:.2f}
"
        f"<b>Entry Zone:</b> {entry_zone_text}
"
        f"<b>Stop:</b> ${stop_loss:.2f}
"
        f"<b>Primary Target:</b> ${take_profit:.2f}
"
        f"<b>Targets:</b> {targets_text}
"
        f"<b>R:R:</b> 1:{rr_ratio:.2f}

"
        f"<b>Volume Ratio:</b> {volume_ratio:.2f}x
"
        f"<b>ATR %:</b> {atr_pct:.2f}%
"
        f"<b>ADX:</b> {adx_val:.2f}

"
        f"<b>Why it triggered</b>
{reason_lines}

"
        f"<i>Approve, paper, or reject the setup.</i>"
    )


def format_daily_report(title: str, bullets: Iterable[Any]) -> str:
    body = "
".join(f"• {escape(str(item))}" for item in bullets)
    return f"📊 <b>{escape(title)}</b>

{body}"


def format_scan_status(stats: Mapping[str, Any]) -> str:
    if not stats:
        return "🔎 <b>Scan Status</b>

No scans have been recorded yet."

    return (
        "🔎 <b>Scan Status</b>

"
        f"<b>Label:</b> {escape(str(stats.get('scan_label', 'unknown')))}
"
        f"<b>Run Time:</b> {escape(str(stats.get('scan_timestamp_utc', 'n/a')))}
"
        f"<b>Universe Loaded:</b> {stats.get('universe_loaded', 0)}
"
        f"<b>Symbols Evaluated:</b> {stats.get('symbols_evaluated', 0)}
"
        f"<b>Qualified Setups:</b> {stats.get('qualified_setups', 0)}
"
        f"<b>Errors:</b> {stats.get('errors', 0)}
"
        f"<b>Top Symbols:</b> {escape(', '.join(stats.get('top_symbols', [])[:10]) or 'None')}"
    )
