from __future__ import annotations

from html import escape
from typing import Any, Iterable, Mapping


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


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
