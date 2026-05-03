from __future__ import annotations

from html import escape
from typing import Any, Mapping, Sequence


EXECUTION_STYLE_LABELS = {
    "day_trade": "Day Trade",
    "swing_trade": "Swing Trade",
    "options": "Options",
}


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _fmt_pct(value: Any, digits: int = 2) -> str:
    num = _to_float(value)
    if abs(num) <= 1.0:
        return f"{num * 100:.{digits}f}%"
    return f"{num:.{digits}f}%"


def _execution_style_title(value: str | None) -> str:
    return EXECUTION_STYLE_LABELS.get(str(value or "day_trade"), str(value or "day_trade").replace("_", " ").title())


def _format_expiry(settings: Mapping[str, Any]) -> str:
    mode = str(settings.get("expiry_mode", "weekly")).lower()
    value = int(settings.get("expiry_value", 0) or 0)
    if mode == "0dte":
        return "0DTE"
    if mode == "weekly":
        return f"{value} week{'s' if value != 1 else ''} out"
    if mode == "monthly":
        return f"{value} month{'s' if value != 1 else ''} out"
    return escape(str(mode))


def format_daily_report(title: str, sections: Mapping[str, Sequence[str]]) -> str:
    lines = [f"<b>{escape(str(title))}</b>"]
    for heading, items in sections.items():
        lines.append("")
        lines.append(f"<b>{escape(str(heading)).upper()}</b>")
        for item in items:
            lines.append(f"• {escape(str(item))}")
    return "\n".join(lines)


def format_tomorrow_plan(items: Sequence[str]) -> str:
    lines = ["<b>Tomorrow Plan</b>", ""]
    lines.extend(f"• {escape(str(item))}" for item in items)
    return "\n".join(lines)


def format_trade_alert(payload: Mapping[str, Any]) -> str:
    symbol = escape(str(payload.get("symbol", "N/A")))
    setup = escape(str(payload.get("setup", payload.get("strategy", "setup"))))
    side = escape(str(payload.get("side", payload.get("action", "LONG"))))
    entry = payload.get("entry") or payload.get("entry_price") or payload.get("price")
    stop = payload.get("stop") or payload.get("stop_loss")
    target = payload.get("target") or payload.get("take_profit")
    rr = payload.get("rr") or payload.get("risk_reward") or payload.get("rr_ratio")
    lines = ["🚨 <b>Trade Alert</b>", "", f"<b>Symbol:</b> {symbol}", f"<b>Setup:</b> {setup}", f"<b>Side:</b> {side}"]
    if entry is not None:
        lines.append(f"<b>Entry:</b> ${_to_float(entry):.2f}")
    if stop is not None:
        lines.append(f"<b>Stop:</b> ${_to_float(stop):.2f}")
    if target is not None:
        lines.append(f"<b>Target:</b> ${_to_float(target):.2f}")
    if rr is not None:
        lines.append(f"<b>R/R:</b> {escape(str(rr))}")
    if payload.get("trade_id"):
        lines.append(f"<b>Trade ID:</b> {escape(str(payload['trade_id']))}")
    return "\n".join(lines)


def format_scan_status(stats: Mapping[str, Any]) -> str:
    def _line_value(key: str, default: Any = 0) -> Any:
        return stats.get(key, default)

    lines = [
        "🔎 <b>Scan Status</b>",
        "",
        f"<b>Profile:</b> {escape(str(stats.get('profile', stats.get('scan_type', 'n/a'))))}",
        f"<b>Snapshot Rows:</b> {_line_value('snapshot_row_count', 'n/a')}",
        f"<b>Snapshot Skipped:</b> {_line_value('snapshot_skipped', 0)}",
        f"<b>Universe Loaded:</b> {_line_value('universe_loaded')}",
        f"<b>Discovery Candidates:</b> {_line_value('discovery_candidates', _line_value('symbols_considered', 0))}",
        f"<b>Lightweight Passers:</b> {_line_value('lightweight_watchlist_count', _line_value('passed_universe_filters', 0))}",
        f"<b>Evaluated:</b> {_line_value('evaluated', 0)}",
        f"<b>Qualified:</b> {_line_value('qualified', 0)}",
        f"<b>Rate Limited:</b> {_line_value('rate_limited', 0)}",
        f"<b>Errors:</b> {_line_value('errors', 0)}",
    ]

    if stats.get("no_candidate_reason"):
        lines.append(f"<b>No Candidate Reason:</b> {escape(str(stats.get('no_candidate_reason')))}")

    rejection_counts = stats.get("rejection_counts") or stats.get("rejection_breakdown") or {}
    if isinstance(rejection_counts, Mapping) and rejection_counts:
        lines.append("")
        lines.append("<b>Rejection Breakdown</b>")
        for reason, count in sorted(rejection_counts.items(), key=lambda item: str(item[0]))[:8]:
            lines.append(f"• {escape(str(reason))}: {escape(str(count))}")

    examples = stats.get("error_examples") or stats.get("rejected_examples") or []
    if isinstance(examples, Mapping):
        examples = [f"{key}: {value}" for key, value in list(examples.items())[:8]]
    if examples:
        lines.append("")
        lines.append("<b>Examples</b>")
        for item in list(examples)[:8]:
            lines.append(f"• {escape(str(item))}")

    return "\n".join(lines)


def format_chain_summary(summary: Mapping[str, Any]) -> str:
    return (
        "⛓ <b>Options Chain Summary</b>\n\n"
        f"<b>Contracts:</b> {summary.get('contract_count', 0)}\n"
        f"<b>Calls:</b> {summary.get('call_count', 0)}\n"
        f"<b>Puts:</b> {summary.get('put_count', 0)}\n"
        f"<b>Total OI:</b> {summary.get('total_open_interest', 0)}\n"
        f"<b>Total Volume:</b> {summary.get('total_volume', 0)}\n"
        f"<b>Avg Mark:</b> ${_to_float(summary.get('avg_mark')):.2f}"
    )


def format_ladder_submission(result: Mapping[str, Any]) -> str:
    entries = result.get("entries", [])
    profile = result.get("profile", {})
    lines = [
        "🎯 <b>Entry / Exit Ladder Plan</b>",
        "",
        f"<b>Symbol:</b> {escape(str(result.get('symbol', 'N/A')))}",
        f"<b>Mode:</b> {escape(str(result.get('mode', 'N/A')))}",
        f"<b>Strategy:</b> {escape(str(result.get('strategy', 'N/A')))}",
    ]
    if result.get("execution_profile"):
        lines.append(f"<b>Execution Style:</b> {escape(_execution_style_title(result.get('execution_profile')))}")
    lines.extend([
        f"<b>Ladder Steps:</b> {profile.get('ladder_steps', len(entries))}",
        "",
    ])
    if not entries:
        lines.append("No ladder entries were generated.")
    else:
        lines.extend(
            f"• Step {row.get('step')}: {row.get('action')} {row.get('qty')} @ ${_to_float(row.get('limit_price')):.2f}"
            for row in entries
        )
    return "\n".join(lines)


def format_exit_ladder_submission(result: Mapping[str, Any]) -> str:
    exits = result.get("exits", [])
    lines = [
        "🏁 <b>Exit Ladder Plan</b>",
        "",
        f"<b>Symbol:</b> {escape(str(result.get('symbol', 'N/A')))}",
        f"<b>Mode:</b> {escape(str(result.get('mode', 'N/A')))}",
        f"<b>Strategy:</b> {escape(str(result.get('strategy', 'N/A')))}",
    ]
    if result.get("execution_profile"):
        lines.append(f"<b>Execution Style:</b> {escape(_execution_style_title(result.get('execution_profile')))}")
    lines.extend([
        f"<b>Risk / Unit:</b> ${_to_float(result.get('risk_per_unit')):.2f}",
        "",
    ])
    if not exits:
        lines.append("No exit ladder legs were generated.")
    else:
        lines.extend(
            f"• Step {row.get('step')}: {row.get('action')} {row.get('qty')} @ ${_to_float(row.get('limit_price')):.2f} | RR {row.get('rr_target')}"
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
        if item.get("error"):
            lines.append(
                f"• Step {leg.get('step')}: {leg.get('side')} {leg.get('qty')} -> ERROR: {escape(str(item.get('error')))}"
            )
            continue
        res = item.get("result", {})
        lines.append(
            f"• Step {leg.get('step')}: {leg.get('side')} {leg.get('qty')} @ ${_to_float(leg.get('limit_price')):.2f} -> {escape(str(res.get('status', 'submitted')))}"
        )
    return "\n".join(lines)


def format_triggered_exit_result(result: Mapping[str, Any]) -> str:
    rows = result.get("results", [])
    lines = ["🧯 <b>Trailing Exit Execution</b>", "", f"<b>Triggered:</b> {result.get('triggered', 0)}", ""]
    if not rows:
        lines.append("No triggered exits were submitted.")
        return "\n".join(lines)
    for item in rows:
        payload = item.get("payload", {})
        position_id = item.get("position_id", "N/A")
        if item.get("error"):
            lines.append(f"• {escape(str(position_id))}: ERROR {escape(str(item['error']))}")
        else:
            status = item.get("result", {}).get("status") or item.get("result", {}).get("order", {}).get("status") or "submitted"
            lines.append(f"• {escape(str(position_id))}: {escape(str(payload.get('side')))} {payload.get('qty')} -> {escape(str(status))}")
    return "\n".join(lines)


def format_open_trails(states: Mapping[str, Any]) -> str:
    if not states:
        return "🧷 <b>Open Trail States</b>\n\nNo trailing states stored."
    lines = ["🧷 <b>Open Trail States</b>", ""]
    for position_id, state in states.items():
        metadata = state.get("metadata") or {}
        pending = " | exit pending" if metadata.get("exit_submitted") else ""
        lines.append(
            f"• {escape(str(position_id))}: {escape(str(state.get('symbol', 'N/A')))} | "
            f"qty {state.get('quantity', 0)} | best ${_to_float(state.get('best_price')):.2f} | "
            f"stop ${_to_float(state.get('active_stop')):.2f} | hit={state.get('stop_hit', False)}{pending}"
        )
    return "\n".join(lines)


def format_position_sync_result(rows: Mapping[str, Any]) -> str:
    if not rows:
        return "🔄 <b>Position Sync Result</b>\n\nNo live positions found."
    lines = ["🔄 <b>Position Sync Result</b>", ""]
    for position_id, state in rows.items():
        if isinstance(state, dict) and state.get("error"):
            lines.append(f"• {escape(str(position_id))}: ERROR {escape(str(state.get('error')))}")
            continue
        if position_id == "pruned_positions":
            removed = state.get("removed", []) if isinstance(state, dict) else []
            lines.append(f"• pruned: {len(removed)} removed")
            continue
        lines.append(
            f"• {escape(str(position_id))}: {escape(str(state.get('symbol', 'N/A')))} | "
            f"broker {escape(str(state.get('broker', 'n/a')))} | qty {state.get('quantity', 0)} | "
            f"price ${_to_float(state.get('current_price')):.2f} | stop ${_to_float(state.get('active_stop')):.2f} | "
            f"hit={state.get('stop_hit', False)}"
        )
    return "\n".join(lines)


def format_options_settings(settings: Mapping[str, Any]) -> str:
    return (
        "🧾 <b>Option Filters</b>\n\n"
        f"<b>Enabled:</b> {settings.get('enabled')}\n"
        f"<b>Delta Min:</b> {settings.get('delta_min')}\n"
        f"<b>Delta Max:</b> {settings.get('delta_max')}\n"
        f"<b>Min Open Interest:</b> {settings.get('min_open_interest')}\n"
        f"<b>Min Daily Volume:</b> {settings.get('min_daily_volume')}\n"
        f"<b>Contract Min Price:</b> ${_to_float(settings.get('contract_min_price')):.2f}\n"
        f"<b>Contract Max Price:</b> ${_to_float(settings.get('contract_max_price')):.2f}\n"
        f"<b>Expiry:</b> {_format_expiry(settings)}\n"
        f"<b>Chain Symbol:</b> {escape(str(settings.get('chain_symbol', 'N/A')))}"
    )


def format_execution_settings(settings: Mapping[str, Any], style: str = "day_trade") -> str:
    return (
        f"🛡 <b>Execution Settings — {_execution_style_title(style)}</b>\n\n"
        f"<b>Risk %:</b> {_fmt_pct(settings.get('risk_pct', 0.01))}\n"
        f"<b>ATR Multiplier:</b> {settings.get('atr_multiplier', 1.0)}\n"
        f"<b>Take Profit:</b> {_fmt_pct(settings.get('take_profit', 0.05))}\n"
        f"<b>Stop Loss:</b> {_fmt_pct(settings.get('stop_loss', 0.02))}\n"
        f"<b>Position Mode:</b> {escape(str(settings.get('position_mode', 'auto')))}\n"
        f"<b>Max Spread %:</b> {_fmt_pct(settings.get('max_spread_pct', 0.03))}\n"
        f"<b>Min Volume:</b> {settings.get('min_volume', 500000)}\n"
        f"<b>Max Slippage %:</b> {_fmt_pct(settings.get('max_slippage_pct', 0.02))}\n"
        f"<b>Max Concurrent Positions:</b> {settings.get('max_concurrent_positions', 3)}\n"
        f"<b>Max Consecutive Losses:</b> {settings.get('max_consecutive_losses', 3)}\n"
        f"<b>Market Hours Only:</b> {escape(str(settings.get('market_hours_only', True)))}\n"
        f"<b>Allow Premarket:</b> {escape(str(settings.get('allow_premarket_entries', False)))}\n"
        f"<b>Allow Afterhours:</b> {escape(str(settings.get('allow_afterhours_entries', False)))}\n"
        f"<b>Entry Cutoff:</b> {escape(str(settings.get('entry_cutoff_time', settings.get('time_of_day_restrictor', '15:00'))))}\n"
        f"<b>Ladder Steps:</b> {settings.get('ladder_steps', 3)}\n"
        f"<b>Ladder Spacing %:</b> {_fmt_pct(settings.get('ladder_spacing_pct', 0.01))}\n"
        f"<b>Trail Type:</b> {escape(str(settings.get('trail_type', 'percent')))}\n"
        f"<b>Trail Value:</b> {_fmt_pct(settings.get('trail_value', 0.02)) if settings.get('trail_type', 'percent') == 'percent' else settings.get('trail_value', 0.02)}"
    )


def format_execution_risk_settings(settings: Mapping[str, Any], style: str = "day_trade") -> str:
    return (
        f"🎯 <b>Risk Settings — {_execution_style_title(style)}</b>\n\n"
        f"<b>Risk %:</b> {_fmt_pct(settings.get('risk_pct', 0.01))}\n"
        f"<b>ATR Multiplier:</b> {settings.get('atr_multiplier', 1.0)}\n"
        f"<b>Take Profit:</b> {_fmt_pct(settings.get('take_profit', 0.05))}\n"
        f"<b>Stop Loss:</b> {_fmt_pct(settings.get('stop_loss', 0.02))}\n"
        f"<b>Position Mode:</b> {escape(str(settings.get('position_mode', 'auto')))}"
    )


def format_execution_safeguards(settings: Mapping[str, Any], style: str = "day_trade") -> str:
    return (
        f"🛡 <b>Safeguards — {_execution_style_title(style)}</b>\n\n"
        f"<b>Max Spread %:</b> {_fmt_pct(settings.get('max_spread_pct', 0.03))}\n"
        f"<b>Min Volume:</b> {settings.get('min_volume', 500000)}\n"
        f"<b>Max Slippage %:</b> {_fmt_pct(settings.get('max_slippage_pct', 0.02))}\n"
        f"<b>Max Concurrent Positions:</b> {settings.get('max_concurrent_positions', 3)}\n"
        f"<b>Max Consecutive Losses:</b> {settings.get('max_consecutive_losses', 3)}\n"
        f"<b>Market Hours Only:</b> {escape(str(settings.get('market_hours_only', True)))}\n"
        f"<b>Allow Premarket:</b> {escape(str(settings.get('allow_premarket_entries', False)))}\n"
        f"<b>Allow Afterhours:</b> {escape(str(settings.get('allow_afterhours_entries', False)))}\n"
        f"<b>Entry Cutoff:</b> {escape(str(settings.get('entry_cutoff_time', settings.get('time_of_day_restrictor', '15:00'))))}"
    )


def format_execution_ladder(settings: Mapping[str, Any], style: str = "day_trade") -> str:
    return (
        f"🪜 <b>Entry Ladder — {_execution_style_title(style)}</b>\n\n"
        f"<b>Ladder Steps:</b> {settings.get('ladder_steps', 3)}\n"
        f"<b>Ladder Spacing %:</b> {_fmt_pct(settings.get('ladder_spacing_pct', 0.01))}"
    )


def format_execution_trailing(settings: Mapping[str, Any], style: str = "day_trade") -> str:
    trail_type = str(settings.get('trail_type', 'percent'))
    value = settings.get('trail_value', 0.02)
    shown = _fmt_pct(value) if trail_type == 'percent' else escape(str(value))
    return (
        f"📌 <b>Trailing Stop — {_execution_style_title(style)}</b>\n\n"
        f"<b>Trail Type:</b> {escape(trail_type)}\n"
        f"<b>Trail Value:</b> {shown}"
    )


def format_ml_weights(weights: Mapping[str, Any]) -> str:
    if not weights:
        return "🧠 <b>ML Weights</b>\n\nNo weights set yet."
    return "🧠 <b>ML Weights</b>\n\n" + "\n".join(f"• {escape(str(k))}: {escape(str(v))}" for k, v in sorted(weights.items()))


def format_sector_status(summary: Mapping[str, Any]) -> str:
    if not summary:
        return "🏭 <b>Sector Status</b>\n\nNo sector data available."
    return "🏭 <b>Sector Status</b>\n\n" + "\n".join(f"• {escape(str(k))}: {v}" for k, v in summary.items())


def format_flow_status(summary: Mapping[str, Any]) -> str:
    return (
        "🌊 <b>Options Flow Status</b>\n\n"
        f"<b>Flows:</b> {summary.get('flow_count', 0)}\n"
        f"<b>Bullish:</b> {summary.get('bullish_flows', 0)}\n"
        f"<b>Bearish:</b> {summary.get('bearish_flows', 0)}\n"
        f"<b>Total Premium:</b> ${_to_float(summary.get('total_premium')):,.2f}\n"
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


def _fmt_number(value: Any, digits: int = 2) -> str:
    try:
        num = float(value)
    except Exception:
        return "n/a"
    if abs(num) >= 1_000_000_000:
        return f"{num / 1_000_000_000:.{digits}f}B"
    if abs(num) >= 1_000_000:
        return f"{num / 1_000_000:.{digits}f}M"
    if abs(num) >= 1_000:
        return f"{num:,.0f}"
    return f"{num:.{digits}f}"


def format_ticker_scan_result(result: Mapping[str, Any]) -> str:
    symbol = escape(str(result.get("symbol", "N/A")))
    scan_type = escape(str(result.get("scan_type", "market")).replace("_", " ").title())
    lines = [f"🎯 <b>Ticker Scan — {symbol}</b>", "", f"<b>Scan Type:</b> {scan_type}"]

    if result.get("error"):
        lines.append("<b>Status:</b> ERROR")
        err = str(result.get("error"))
        if err == "empty_market_data":
            err = "No equity OHLCV market data found. Use stock/ETF tickers here, or use Options Chain/Ticker Research for index-option symbols."
        lines.append(f"<b>Error:</b> {escape(err)}")
        return "\n".join(lines)

    if "passed_filters" in result:
        lines.append(f"<b>Passed Filters:</b> {'YES' if result.get('passed_filters') else 'NO'}")
    if "strategy_signal" in result:
        lines.append(f"<b>Strategy Signal:</b> {'YES' if result.get('strategy_signal') else 'NO'}")
    if "qualified" in result:
        lines.append(f"<b>Qualified:</b> {'YES' if result.get('qualified') else 'NO'}")

    price = result.get("price")
    if price is not None:
        lines.append(f"<b>Price:</b> ${_to_float(price):.2f}")
    volume = result.get("volume")
    if volume is not None:
        lines.append(f"<b>Volume:</b> {_fmt_number(volume, 0)}")
    rel_volume = result.get("relative_volume")
    if rel_volume is not None:
        lines.append(f"<b>Relative Volume:</b> {_to_float(rel_volume):.2f}x")
    atr_pct = result.get("atr_pct")
    if atr_pct is not None:
        lines.append(f"<b>ATR %:</b> {_fmt_pct(atr_pct)}")
    gap_pct = result.get("gap_pct")
    if gap_pct is not None:
        lines.append(f"<b>Gap %:</b> {_fmt_pct(gap_pct)}")

    setup = result.get("setup") or result.get("strategy")
    if setup:
        lines.append(f"<b>Setup:</b> {escape(str(setup))}")
    side = result.get("side") or result.get("action")
    if side:
        lines.append(f"<b>Side:</b> {escape(str(side))}")

    rejection = result.get("rejection_reason")
    if rejection:
        lines.append(f"<b>Reason:</b> {escape(str(rejection))}")

    news_count = result.get("news_count")
    if news_count is not None:
        lines.append(f"<b>News Count:</b> {news_count}")
    headlines = result.get("headlines") or result.get("catalyst_headlines") or []
    if headlines:
        lines.append("")
        lines.append("<b>Headlines:</b>")
        for item in list(headlines)[:5]:
            lines.append(f"• {escape(str(item))}")

    return "\n".join(lines)


def format_ticker_research_result(payload: Mapping[str, Any]) -> str:
    symbol = escape(str(payload.get("symbol", "N/A")))
    scan_type = escape(str(payload.get("scan_type", "market")).replace("_", " ").title())
    status = escape(str(payload.get("status", "UNKNOWN")))
    scan = payload.get("scan") or {}
    daily = payload.get("daily") or {}
    news = payload.get("news") or {}
    options = payload.get("options") or {}
    option_summary = options.get("summary") or {}
    iv = options.get("iv") or {}
    flow = options.get("flow") or {}

    lines = [f"🧭 <b>Ticker Research — {symbol}</b>", "", f"<b>Scan Type:</b> {scan_type}", f"<b>Status:</b> {status}"]
    if payload.get("reason"):
        lines.append(f"<b>Reason:</b> {escape(str(payload.get('reason')))}")

    lines.append("")
    lines.append("<b>Equity Scan</b>")
    if scan.get("error"):
        err = str(scan.get("error"))
        if err == "empty_market_data":
            err = "No equity OHLCV data found."
        lines.append(f"• Error: {escape(err)}")
    else:
        lines.append(f"• Passed Filters: {'YES' if scan.get('passed_filters') else 'NO'}")
        lines.append(f"• Strategy Signal: {'YES' if scan.get('strategy_signal') else 'NO'}")
        lines.append(f"• Qualified: {'YES' if scan.get('qualified') else 'NO'}")
        if scan.get("rejection_reason"):
            lines.append(f"• Reason: {escape(str(scan.get('rejection_reason')))}")

    lines.append("")
    lines.append("<b>Daily Context</b>")
    if daily.get("available"):
        lines.append(f"• Last Close: ${_to_float(daily.get('last_close')):.2f}")
        lines.append(f"• Volume: {_fmt_number(daily.get('latest_volume'), 0)}")
        lines.append(f"• Rel Volume: {_to_float(daily.get('relative_volume')):.2f}x")
        lines.append(f"• Trend: {escape(str(daily.get('trend', 'neutral')))}")
        if daily.get("change_pct") is not None:
            lines.append(f"• Change: {_fmt_pct(daily.get('change_pct'))}")
        if daily.get("atr_pct") is not None:
            lines.append(f"• ATR: {_fmt_pct(daily.get('atr_pct'))}")
    else:
        lines.append(f"• {escape(str(daily.get('error', 'No daily data')))}")

    lines.append("")
    lines.append("<b>Options</b>")
    if options.get("error"):
        lines.append(f"• {escape(str(options.get('error')))}")
    elif option_summary:
        lines.append(f"• Contracts: {option_summary.get('contract_count', 0)}")
        lines.append(f"• Calls/Puts: {option_summary.get('call_count', 0)} / {option_summary.get('put_count', 0)}")
        lines.append(f"• Total OI: {_fmt_number(option_summary.get('total_open_interest'), 0)}")
        lines.append(f"• Total Volume: {_fmt_number(option_summary.get('total_volume'), 0)}")
        lines.append(f"• Avg Mark: ${_to_float(option_summary.get('avg_mark')):.2f}")
        if iv:
            lines.append(f"• IV Regime: {escape(str(iv.get('iv_regime', 'unknown')))}")
        if flow:
            lines.append(f"• Flow Bias: {escape(str(flow.get('bias', 'neutral')))}")
    else:
        lines.append("• No options snapshot available.")

    lines.append("")
    lines.append(f"<b>News Count:</b> {news.get('news_count', 0)}")
    headlines = news.get("headlines") or scan.get("headlines") or []
    if headlines:
        for item in list(headlines)[:4]:
            lines.append(f"• {escape(str(item))}")

    lines.append("")
    lines.append("<i>Saved to ticker research history.</i>")
    return "\n".join(lines)


def format_ticker_history(rows: Sequence[Mapping[str, Any]], symbol: str | None = None) -> str:
    title = f"Ticker History — {escape(symbol.upper())}" if symbol else "Ticker Research History"
    if not rows:
        return f"🗂 <b>{title}</b>\n\nNo saved ticker research rows yet."
    lines = [f"🗂 <b>{title}</b>", ""]
    for row in rows:
        created = str(row.get("created_at", ""))[:19].replace("T", " ")
        line = (
            f"• {escape(str(row.get('symbol', 'N/A')))} | "
            f"{escape(str(row.get('scan_type', 'market')))} | "
            f"{escape(str(row.get('status', 'UNKNOWN')))} | "
            f"price ${_to_float(row.get('price')):.2f} | "
            f"opts {row.get('option_contracts', 0)} | "
            f"{escape(created)}"
        )
        if row.get("reason"):
            line += f" | {escape(str(row.get('reason')))}"
        lines.append(line)
    return "\n".join(lines)

def format_simple_lines(title: str, lines_in: Sequence[str]) -> str:
    lines = [f"<b>{escape(str(title))}</b>", ""]
    lines.extend(f"• {escape(str(line))}" for line in lines_in)
    return "\n".join(lines)
