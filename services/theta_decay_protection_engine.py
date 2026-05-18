from __future__ import annotations

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo


class ThetaDecayProtectionEngine:
    """0DTE theta-decay protection intelligence.

    Converts time-of-day, execution quality, trap risk, runner quality, and
    session state into premium-protection instructions for SPY/XSP tactical
    execution.
    """

    def __init__(self):
        self.market_tz = ZoneInfo("America/New_York")

    def evaluate(
        self,
        probabilities: dict[str, Any],
        execution_timing: dict[str, Any],
        adaptive_exits: dict[str, Any],
        autonomous_scaling: dict[str, Any],
        session_personality: dict[str, Any],
        trap_detection: dict[str, Any],
        rsi_5m: float,
        latest: float,
        vwap: float,
    ) -> dict[str, Any]:
        now = datetime.now(self.market_tz)
        minutes = now.hour * 60 + now.minute

        trend_probability = int(probabilities.get("trend_probability") or 0)
        runner_probability = int(probabilities.get("runner_probability") or 0)
        trap_probability = int(probabilities.get("trap_probability") or 0)
        mean_reversion_probability = int(probabilities.get("mean_reversion_probability") or 0)
        timing_score = int(execution_timing.get("timing_score") or 50)
        hold_strength = int(adaptive_exits.get("hold_strength") or 50)

        session_state = str(execution_timing.get("session_state") or "normal_session_conditions")
        personality = str(session_personality.get("session_personality") or session_personality.get("personality") or "balanced")
        trap_risk = str(trap_detection.get("trap_risk") or trap_detection.get("risk_level") or "normal")
        scaling_mode = str(autonomous_scaling.get("scaling_mode") or autonomous_scaling.get("mode") or "standard")

        theta_risk_score = self._base_time_decay_score(minutes)
        premium_hold_score = 50
        action_items: list[str] = []
        protections: list[str] = []
        blockers: list[str] = []

        theta_risk_score += int((trap_probability - 50) * 0.35)
        theta_risk_score += int((mean_reversion_probability - 50) * 0.25)
        theta_risk_score -= int((trend_probability - 50) * 0.20)
        theta_risk_score -= int((runner_probability - 50) * 0.20)

        premium_hold_score += int((hold_strength - 50) * 0.45)
        premium_hold_score += int((timing_score - 50) * 0.30)
        premium_hold_score += int((runner_probability - 50) * 0.25)
        premium_hold_score -= int((theta_risk_score - 50) * 0.35)

        if session_state == "midday_decay_window":
            theta_risk_score += 18
            premium_hold_score -= 12
            protections.append("Midday decay window active; premium bleed risk is elevated.")

        if session_state == "power_hour_window" and trend_probability >= 60:
            theta_risk_score -= 8
            premium_hold_score += 8
            action_items.append("Late-day expansion can justify holding only after confirmation.")

        if trap_probability >= 60 or "high" in trap_risk or "elevated" in trap_risk:
            theta_risk_score += 12
            premium_hold_score -= 10
            blockers.append("Trap risk conflicts with holding exposed 0DTE premium.")

        if mean_reversion_probability >= 65:
            theta_risk_score += 10
            blockers.append("Mean-reversion control favors fast exits instead of premium holding.")

        if runner_probability >= 60 and trend_probability >= 60 and latest > vwap:
            premium_hold_score += 12
            action_items.append("Runner permission can stay active while price holds VWAP control.")

        if rsi_5m >= 72:
            theta_risk_score += 8
            premium_hold_score -= 8
            protections.append("RSI extension increases reversal plus premium-crush risk.")

        if "aggressive" in scaling_mode and theta_risk_score >= 65:
            blockers.append("Aggressive scaling should be blocked until theta risk cools.")

        if "chop" in personality.lower() or "rotation" in personality.lower():
            theta_risk_score += 8
            protections.append("Choppy personality requires reduced exposure duration.")

        theta_risk_score = self._clamp(theta_risk_score)
        premium_hold_score = self._clamp(premium_hold_score)

        protection_mode = self._protection_mode(theta_risk_score, premium_hold_score)
        max_hold_minutes = self._max_hold_minutes(theta_risk_score, premium_hold_score, minutes)
        runner_permission = premium_hold_score >= 62 and theta_risk_score <= 58 and runner_probability >= 55

        if protection_mode in {"critical_decay_defense", "defensive_decay_control"}:
            protections.append("Take partials faster and avoid letting winners turn into theta losses.")

        if runner_permission:
            action_items.append("Runner can remain open only after partial profit and structure confirmation.")
        else:
            protections.append("Runner exposure should stay limited until premium hold quality improves.")

        return {
            "protection_mode": protection_mode,
            "theta_risk_score": theta_risk_score,
            "premium_hold_score": premium_hold_score,
            "max_hold_minutes": max_hold_minutes,
            "runner_permission": runner_permission,
            "scaling_permission": theta_risk_score <= 62,
            "recommended_contract_style": self._contract_style(theta_risk_score, premium_hold_score),
            "actions": action_items[:6] or ["Use standard premium protection while waiting for cleaner confirmation."],
            "protections": protections[:6],
            "blockers": blockers[:6],
        }

    def _base_time_decay_score(self, minutes: int) -> int:
        if minutes < 570:
            return 35
        if 570 <= minutes <= 630:
            return 45
        if 631 <= minutes <= 690:
            return 52
        if 691 <= minutes <= 810:
            return 72
        if 811 <= minutes <= 900:
            return 62
        if 901 <= minutes <= 960:
            return 68
        return 80

    def _max_hold_minutes(self, theta_risk: int, premium_hold: int, minutes: int) -> int:
        if theta_risk >= 75:
            return 5
        if theta_risk >= 65:
            return 8
        if premium_hold >= 70 and 570 <= minutes <= 930:
            return 25
        if premium_hold >= 60:
            return 15
        return 10

    def _protection_mode(self, theta_risk: int, premium_hold: int) -> str:
        if theta_risk >= 78:
            return "critical_decay_defense"
        if theta_risk >= 65:
            return "defensive_decay_control"
        if premium_hold >= 68:
            return "controlled_runner_permission"
        if premium_hold >= 55:
            return "balanced_premium_management"
        return "fast_scalp_decay_protection"

    def _contract_style(self, theta_risk: int, premium_hold: int) -> str:
        if theta_risk >= 70:
            return "higher-delta contracts only; avoid cheap far OTM premium"
        if premium_hold >= 68:
            return "liquid ATM/near-ATM contracts with runner only after partials"
        return "tight-spread ATM contracts with fast profit protection"

    def _clamp(self, value: int) -> int:
        return max(5, min(95, int(value)))
