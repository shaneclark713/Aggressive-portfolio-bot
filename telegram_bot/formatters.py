from __future__ import annotations

from html import escape
from typing import Any, Mapping


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def format_profile_execution_status(mode: str, strategy: str, profile: Mapping[str, Any]) -> str:
    lines = ["⚙ <b>Profile Execution Status</b>", "", f"<b>Mode:</b> {escape(str(mode))}", f"<b>Strategy:</b> {escape(str(strategy))}", ""]
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
        f"<b>Avg Mark:</b> ${_to_float(summary.get('avg_mark')):.2f}"
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
        f"• Step {row.get('step')}: {row.get('action')} {row.get('qty')} @ ${_to_float(row.get('limit_price')):.2f}"
        for row in entries
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
            f"• Step {leg.get('step')}: {leg.get('side')} {leg.get('qty')} @ ${_to_float(leg.get('limit_price')):.2f} -> {escape(str(res.get('status', 'submitted')))}"
        )
    return "\n".join(lines)


def format_open_trails(states: Mapping[str, Any]) -> str:
    if not states:
        return "🧷 <b>Open Trail States</b>\n\nNo trailing states stored."
    lines = ["🧷 <b>Open Trail States</b>", ""]
    for position_id, state in states.items():
        lines.append(
            f"• {escape(str(position_id))}: entry ${_to_float(state.get('entry_price')):.2f}, "
            f"best ${_to_float(state.get('best_price')):.2f}, stop ${_to_float(state.get('active_stop')):.2f}"
        )
    return "\n".join(lines)


def format_position_sync_result(rows: Mapping[str, Any]) -> str:
    lines = ["🔄 <b>Position Sync Result</b>", ""]
    for position_id, state in rows.items():
        lines.append(
            f"• {escape(str(position_id))}: {escape(str(state.get('symbol', 'N/A')))} | "
            f"best ${_to_float(state.get('best_price')):.2f} | stop ${_to_float(state.get('active_stop')):.2f} | "
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
        f"<b>Risk %:</b> {settings.get('risk_pct', 0.75)}\n"
        f"<b>ATR Multiplier:</b> {settings.get('atr_multiplier', 1.0)}\n"
        f"<b>Position Mode:</b> {settings.get('position_mode', 'auto')}\n"
        f"<b>Max Spread %:</b> {settings.get('max_spread_pct', 0.03)}\n"
        f"<b>Min Volume:</b> {settings.get('min_volume', 500000)}\n"
        f"<b>Max Slippage %:</b> {settings.get('max_slippage_pct', 0.02)}\n"
        f"<b>Ladder Steps:</b> {settings.get('ladder_steps', 3)}\n"
        f"<b>Ladder Spacing %:</b> {settings.get('ladder_spacing_pct', 0.01)}\n"
        f"<b>Trail Type:</b> {escape(str(settings.get('trail_type', 'percent')))}\n"
        f"<b>Trail Value:</b> {settings.get('trail_value', 0.02)}"
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
