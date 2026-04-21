from __future__ import annotations

from html import escape
from typing import Any, Mapping, Sequence


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _to_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except Exception:
        return default


def _fmt_money(value: Any) -> str:
    return f"${_to_float(value):,.2f}"


def _fmt_pct(value: Any) -> str:
    numeric = _to_float(value)
    if abs(numeric) <= 1:
        numeric *= 100
    return f"{numeric:.2f}%"


def _line_list(items: Sequence[str], empty: str = "None") -> str:
    if not items:
        return empty
    return "\n".join(f"• {escape(str(item))}" for item in items)


def format_daily_report(title: str, sections: Mapping[str, Sequence[str]] | Sequence[str]) -> str:
    lines = [f"<b>{escape(str(title))}</b>", ""]

    if isinstance(sections, Mapping):
        for section_name, items in sections.items():
            lines.append(f"<b>{escape(str(section_name))}</b>")
            if items:
                for item in items:
                    lines.append(f"• {escape(str(item))}")
            else:
                lines.append("• None")
            lines.append("")
    else:
        for item in sections:
            lines.append(f"• {escape(str(item))}")

    return "\n".join(lines).strip()


def format_trade_alert(payload: Mapping[str, Any]) -> str:
    symbol = escape(str(payload.get("symbol", "N/A")))
    strategy = escape(str(payload.get("strategy", "unknown")))
    side = escape(str(payload.get("side", "buy")).upper())
    qty = _to_int(payload.get("quantity", payload.get("qty", 1)), 1)
    entry = payload.get("entry") or payload.get("entry_price") or payload.get("price")
    stop = payload.get("stop") or payload.get("stop_loss") or payload.get("stop_price")
    target = payload.get("target") or payload.get("target_price") or payload.get("take_profit")
    rr = payload.get("risk_reward") or payload.get("rr") or payload.get("rr_ratio") or payload.get("r_multiple")
    broker = escape(str(payload.get("broker", "ALPACA")))
    instrument_type = escape(str(payload.get("instrument_type", "stock")))
    mode = escape(str(payload.get("mode", "alerts_only")))
    trade_id = payload.get("trade_id", "N/A")
    timeframe = payload.get("timeframe")
    catalyst = payload.get("catalyst") or payload.get("reason")

    lines = [
        "🚨 <b>Trade Candidate</b>",
        "",
        f"<b>ID:</b> {escape(str(trade_id))}",
        f"<b>Symbol:</b> {symbol}",
        f"<b>Side:</b> {side}",
        f"<b>Qty:</b> {qty}",
        f"<b>Strategy:</b> {strategy}",
        f"<b>Instrument:</b> {instrument_type}",
        f"<b>Broker:</b> {broker}",
        f"<b>Mode:</b> {mode}",
    ]

    if timeframe:
        lines.append(f"<b>Timeframe:</b> {escape(str(timeframe))}")
    if entry is not None:
        lines.append(f"<b>Entry:</b> {_fmt_money(entry)}")
    if stop is not None:
        lines.append(f"<b>Stop:</b> {_fmt_money(stop)}")
    if target is not None:
        lines.append(f"<b>Target:</b> {_fmt_money(target)}")
    if rr is not None:
        lines.append(f"<b>R:R:</b> {escape(str(rr))}")
    if catalyst:
        lines.extend(["", f"<b>Setup Notes:</b> {escape(str(catalyst))}"])

    return "\n".join(lines)


def format_tomorrow_plan(items: Sequence[str]) -> str:
    lines = ["🗓 <b>Tomorrow Plan</b>", ""]
    for item in items:
        lines.append(f"• {escape(str(item))}")
    return "\n".join(lines)


def format_profile_execution_status(mode: str, strategy: str, profile: Mapping[str, Any]) -> str:
    lines = [
        "⚙ <b>Profile Execution Status</b>",
        "",
        f"<b>Mode:</b> {escape(str(mode))}",
        f"<b>Strategy:</b> {escape(str(strategy))}",
        "",
    ]
    for key, value in profile.items():
        lines.append(f"<b>{escape(str(key))}:</b> {escape(str(value))}")
    return "\n".join(lines)


def format_chain_summary(summary: Mapping[str, Any]) -> str:
    return (
        "⛓ <b>Options Chain Summary</b>\n\n"
        f"<b>Contracts:</b> {summary.get('contract_count', 0)}\n"
        f"<b>Calls:</b> {summary.get('call_count', 0)}\n"
        f"<b>Puts:</b> {summary.get('put_count', 0)}\n"
        f"<b>Total OI:</b> {summary.get('total_open_interest', 0)}\n"
        f"<b>Total Volume:</b> {summary.get('total_volume', 0)}\n"
        f"<b>Avg Mark:</b> {_fmt_money(summary.get('avg_mark'))}"
    )


def format_ladder_submission(result: Mapping[str, Any]) -> str:
    entries = result.get("entries", [])
    profile = result.get("profile", {})
    lines = [
        "🚀 <b>Ladder Submission Plan</b>",
        "",
        f"<b>Symbol:</b> {escape(str(result.get('symbol', 'N/A')))}",
        f"<b>Mode:</b> {escape(str(result.get('mode', 'N/A')))}",
        f"<b>Strategy:</b> {escape(str(result.get('strategy', 'N/A')))}",
        f"<b>Ladder Steps:</b> {profile.get('ladder_steps', len(entries))}",
        "",
    ]
    lines.extend(
        f"• Step {row.get('step')}: {row.get('action')} {row.get('qty')} @ {_fmt_money(row.get('limit_price'))}"
        for row in entries
    )
    return "\n".join(lines)


def format_exit_ladder_submission(result: Mapping[str, Any]) -> str:
    exits = result.get("exits", [])
    lines = [
        "🎯 <b>Exit Ladder Plan</b>",
        "",
        f"<b>Symbol:</b> {escape(str(result.get('symbol', 'N/A')))}",
        f"<b>Risk / Unit:</b> {_fmt_money(result.get('risk_per_unit'))}",
        "",
    ]
    lines.extend(
        f"• Step {row.get('step')}: {row.get('action')} {row.get('qty')} @ {_fmt_money(row.get('limit_price'))} (R={row.get('rr_target')})"
        for row in exits
    )
    return "\n".join(lines)


def format_ladder_execution_result(result: Mapping[str, Any]) -> str:
    lines = [
        "📤 <b>Ladder Execution Result</b>",
        "",
        f"<b>Symbol:</b> {escape(str(result.get('symbol', 'N/A')))}",
        f"<b>Submitted Legs:</b> {result.get('submitted_legs', 0)}",
        "",
    ]
    for item in result.get("results", []):
        leg = item.get("leg", {})
        res = item.get("result", {})
        lines.append(
            f"• Step {leg.get('step')}: {leg.get('side')} {leg.get('qty')} @ {_fmt_money(leg.get('limit_price'))} -> {escape(str(res.get('status', res.get('id', 'submitted'))))}"
        )
    return "\n".join(lines)


def format_open_trails(states: Mapping[str, Any]) -> str:
    if not states:
        return "🧷 <b>Open Trail States</b>\n\nNo trailing states stored."
    lines = ["🧷 <b>Open Trail States</b>", ""]
    for position_id, state in states.items():
        if isinstance(state, dict) and state.get("error"):
            lines.append(f"• {escape(str(position_id))}: {escape(str(state.get('error')))}")
            continue
        lines.append(
            f"• {escape(str(position_id))}: {escape(str(state.get('symbol', 'N/A')))} | "
            f"entry {_fmt_money(state.get('entry_price'))} | "
            f"best {_fmt_money(state.get('best_price'))} | stop {_fmt_money(state.get('active_stop'))} | "
            f"stop_hit={state.get('stop_hit', False)}"
        )
    return "\n".join(lines)


def format_position_sync_result(rows: Mapping[str, Any]) -> str:
    if not rows:
        return "🔄 <b>Position Sync Result</b>\n\nNo live positions returned."
    lines = ["🔄 <b>Position Sync Result</b>", ""]
    for position_id, state in rows.items():
        if isinstance(state, dict) and state.get("error"):
            lines.append(f"• {escape(str(position_id))}: {escape(str(state.get('error')))}")
            continue
        lines.append(
            f"• {escape(str(position_id))}: {escape(str(state.get('symbol', 'N/A')))} | "
            f"best {_fmt_money(state.get('best_price'))} | stop {_fmt_money(state.get('active_stop'))} | "
            f"stop_hit={state.get('stop_hit', False)}"
        )
    return "\n".join(lines)


def format_options_settings(settings: Mapping[str, Any]) -> str:
    return (
        "🧾 <b>Options Settings</b>\n\n"
        f"<b>Enabled:</b> {settings.get('enabled')}\n"
        f"<b>Delta Range:</b> {settings.get('delta_min')} - {settings.get('delta_max')}\n"
        f"<b>Min Open Interest:</b> {settings.get('min_open_interest')}\n"
        f"<b>Expiry Preference:</b> {settings.get('expiry_preference')}\n"
        f"<b>Chain Symbol:</b> {escape(str(settings.get('chain_symbol', 'N/A')))}"
    )


def format_execution_settings(settings: Mapping[str, Any]) -> str:
    return (
        "🛡 <b>Execution Settings</b>\n\n"
        f"<b>Risk %:</b> {_fmt_pct(settings.get('risk_pct', 0.75))}\n"
        f"<b>ATR Multiplier:</b> {settings.get('atr_multiplier', 1.0)}\n"
        f"<b>Position Mode:</b> {settings.get('position_mode', 'auto')}\n"
        f"<b>Max Spread %:</b> {_fmt_pct(settings.get('max_spread_pct', 0.03))}\n"
        f"<b>Min Volume:</b> {settings.get('min_volume', 500000)}\n"
        f"<b>Max Slippage %:</b> {_fmt_pct(settings.get('max_slippage_pct', 0.02))}\n"
        f"<b>Ladder Steps:</b> {settings.get('ladder_steps', 3)}\n"
        f"<b>Ladder Spacing %:</b> {_fmt_pct(settings.get('ladder_spacing_pct', 0.01))}\n"
        f"<b>Trail Type:</b> {escape(str(settings.get('trail_type', 'percent')))}\n"
        f"<b>Trail Value:</b> {_fmt_pct(settings.get('trail_value', 0.02))}"
    )


def format_ml_weights(weights: Mapping[str, Any]) -> str:
    if not weights:
        return "🧠 <b>ML Weights</b>\n\nNo weights set yet."
    return "🧠 <b>ML Weights</b>\n\n" + "\n".join(
        f"• {escape(str(k))}: {escape(str(v))}" for k, v in sorted(weights.items())
    )


def format_sector_status(summary: Mapping[str, Any]) -> str:
    if not summary:
        return "🏭 <b>Sector Status</b>\n\nNo sector data available."
    return "🏭 <b>Sector Status</b>\n\n" + "\n".join(
        f"• {escape(str(k))}: {v}" for k, v in summary.items()
    )


def format_flow_status(summary: Mapping[str, Any]) -> str:
    return (
        "🌊 <b>Options Flow Status</b>\n\n"
        f"<b>Flows:</b> {summary.get('flow_count', 0)}\n"
        f"<b>Bullish:</b> {summary.get('bullish_flows', 0)}\n"
        f"<b>Bearish:</b> {summary.get('bearish_flows', 0)}\n"
        f"<b>Total Premium:</b> {_fmt_money(summary.get('total_premium'))}\n"
        f"<b>Bias:</b> {escape(str(summary.get('bias', 'neutral')))}"
    )


def format_iv_status(summary: Mapping[str, Any]) -> str:
    return (
        "📈 <b>IV Status</b>\n\n"
        f"<b>Contracts:</b> {summary.get('contract_count', 0)}\n"
        f"<b>Avg IV:</b> {summary.get('avg_iv', 0)}\n"
        f"<b>Total OI:</b> {summary.get('total_open_interest', 0)}\n"
        f"<b>Total Volume:</b> {summary.get('total_volume', 0)}\n"
        f"<b>Regime:</b> {escape(str(summary.get('iv_regime', 'unknown')))}"
    )


def format_scan_status(stats: Mapping[str, Any]) -> str:
    if not stats:
        return "🔎 <b>Scan Status</b>\n\nNo scan has run yet."
    return (
        "🔎 <b>Scan Status</b>\n\n"
        f"<b>Type:</b> {escape(str(stats.get('scan_type', 'unknown')))}\n"
        f"<b>Universe Loaded:</b> {_to_int(stats.get('universe_loaded'))}\n"
        f"<b>Passed Universe Filters:</b> {_to_int(stats.get('passed_universe_filters'))}\n"
        f"<b>Symbols Evaluated:</b> {_to_int(stats.get('evaluated'))}\n"
        f"<b>Qualified Setups:</b> {_to_int(stats.get('qualified'))}\n"
        f"<b>Rate Limited:</b> {_to_int(stats.get('rate_limited'))}\n"
        f"<b>Errors:</b> {_to_int(stats.get('errors'))}\n"
        f"<b>Top Symbols:</b> {escape(', '.join(stats.get('top_symbols', []) or [])) or 'None'}"
    )


def format_snapshot_status(profile: str, status: Mapping[str, Any]) -> str:
    return (
        "🗂 <b>Snapshot Status</b>\n\n"
        f"<b>Profile:</b> {escape(str(profile))}\n"
        f"<b>Created:</b> {escape(str(status.get('created_at', 'N/A')))}\n"
        f"<b>Rows:</b> {status.get('row_count', 0)}\n"
        f"<b>Skipped:</b> {status.get('skipped', 0)}\n"
        f"<b>Source:</b> {escape(str(status.get('source', 'unknown')))}\n"
        f"<b>Refresh Reason:</b> {escape(str(status.get('refresh_reason', 'unknown')))}"
    )


def format_passing_rows(scan_type: str, rows: list[Mapping[str, Any]], limit: int = 12) -> str:
    if not rows:
        return f"✅ <b>{escape(scan_type.title())} Passers</b>\n\nNo passers right now."
    lines = [f"✅ <b>{escape(scan_type.title())} Passers</b>", ""]
    for row in rows[:limit]:
        lines.append(
            f"• {escape(str(row.get('symbol', 'N/A')))} | {_fmt_money(row.get('price'))} | "
            f"chg {_to_float(row.get('change_pct')):.2f}% | gap {_to_float(row.get('gap_pct')):.2f}%"
        )
    return "\n".join(lines)


def format_scan_overview(scan_type: str, payload: Mapping[str, Any]) -> str:
    if scan_type in {"news"}:
        headlines = list(payload.get("headlines", []) or [])
        return (
            "📰 <b>News Scan</b>\n\n"
            f"<b>Headline Count:</b> {payload.get('headline_count', 0)}\n\n"
            f"{_line_list(headlines, 'No headlines returned.')}"
        )
    if scan_type in {"events"}:
        events = list(payload.get("events", []) or [])
        return (
            "📅 <b>Events Scan</b>\n\n"
            f"<b>Events:</b> {payload.get('event_count', 0)}\n"
            f"<b>High Impact:</b> {payload.get('high_impact_count', 0)}\n\n"
            f"{_line_list(events, 'No events returned.')}"
        )
    if scan_type in {"catalyst"}:
        rows = list(payload.get("catalysts", []) or [])
        lines = [
            "⚡ <b>Catalyst Scan</b>",
            "",
            f"<b>Symbols Checked:</b> {payload.get('symbols_checked', 0)}",
            "",
        ]
        if not rows:
            lines.append("No catalyst rows returned.")
        for row in rows[:6]:
            lines.append(f"<b>{escape(str(row.get('symbol', 'N/A')))}</b> ({row.get('headline_count', 0)} headlines)")
            for headline in row.get("headlines", [])[:2]:
                lines.append(f"• {escape(str(headline))}")
        return "\n".join(lines)

    stats = dict(payload.get("stats") or {})
    candidates = list(payload.get("candidates") or [])
    lines = [
        f"🔭 <b>{escape(scan_type.title())} Scan</b>",
        "",
        f"<b>Qualified:</b> {stats.get('qualified', len(candidates))}",
        f"<b>Evaluated:</b> {stats.get('evaluated', 0)}",
        f"<b>Errors:</b> {stats.get('errors', 0)}",
        "",
    ]
    if not candidates:
        lines.append("No qualified setups returned.")
    for row in candidates[:5]:
        lines.append(
            f"• <b>{escape(str(row.get('symbol', 'N/A')))}</b> | {escape(str(row.get('strategy', 'N/A')))} | "
            f"{escape(str(row.get('signal', 'WAIT')))} | conf {row.get('confidence', 0)} | RR {row.get('rr_ratio', 'N/A')}"
        )
    return "\n".join(lines)


def format_filter_profile_status(profile: str, preset_name: str) -> str:
    return (
        "🎛 <b>Filter Profile</b>\n\n"
        f"<b>Profile:</b> {escape(str(profile))}\n"
        f"<b>Preset:</b> {escape(str(preset_name))}"
    )


def format_strategy_status(states: Mapping[str, Any]) -> str:
    lines = ["🧠 <b>Strategy Toggles</b>", ""]
    for name, value in states.items():
        lines.append(f"• {escape(str(name))}: {'ON' if value else 'OFF'}")
    return "\n".join(lines)


def format_mode_status(mode: str) -> str:
    return f"🎚 <b>Execution Mode</b>\n\n<b>Current:</b> {escape(str(mode))}"
