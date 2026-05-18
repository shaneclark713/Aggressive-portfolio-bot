from __future__ import annotations

from typing import Any


class RiskRegimeEngine:
    """Institutional risk-regime classifier.

    Converts cross-market tone, dealer regime, event risk, theta stress,
    trap probability, and ecosystem consensus into a top-level risk state.
    Advisory only; downstream execution gates must enforce final controls.
    """

    def classify(self, payload: dict[str, Any]) -> dict[str, Any]:
        cross_market = payload.get("cross_market", {}) or {}
        dealer_gamma = payload.get("dealer_gamma", {}) or {}
        probabilities = payload.get("probabilities", {}) or {}
        theta = payload.get("theta_protection", {}) or {}
        ecosystem = payload.get("ecosystem", {}) or {}
        events = payload.get("events", []) or []

        cross_tone = str(cross_market.get("tone") or "mixed / neutral").lower()
        dealer_regime = str(dealer_gamma.get("dealer_regime") or "balanced").lower()
        trend_probability = int(probabilities.get("trend_probability") or 50)
        trap_probability = int(probabilities.get("trap_probability") or 50)
        expansion_probability = int(probabilities.get("gamma_expansion_probability") or 50)
        theta_risk = int(theta.get("theta_risk_score") or 50)
        ecosystem_score = int(ecosystem.get("ecosystem_score") or 50)

        high_impact_count = len(events) if isinstance(events, list) else 0

        regime = "neutral"
        risk_score = 50
        execution_posture = "standard_review"
        blockers: list[str] = []
        controls: list[str] = []
        confirmations: list[str] = []

        if "risk-on" in cross_tone or "supportive" in cross_tone:
            risk_score += 10
            confirmations.append("Cross-market tone supports risk participation.")
        if "risk-off" in cross_tone or "defensive" in cross_tone:
            risk_score -= 15
            controls.append("Cross-market tone is defensive; reduce autonomy.")

        if "pin" in dealer_regime:
            risk_score -= 12
            controls.append("Dealer pin regime requires range-control posture.")
        elif "chase" in dealer_regime or "hedge" in dealer_regime:
            risk_score += 8
            confirmations.append("Dealer regime supports directional pressure.")

        if high_impact_count > 0:
            risk_score -= min(20, high_impact_count * 5)
            controls.append("High-impact event risk active; tighten execution controls.")

        if theta_risk >= 70:
            risk_score -= 18
            blockers.append("Theta stress is too high for aggressive deployment.")
        elif theta_risk >= 62:
            risk_score -= 8
            controls.append("Theta risk elevated; limit hold duration.")

        if trap_probability >= 65:
            risk_score -= 18
            blockers.append("Trap probability is too high for autonomous aggression.")
        elif trap_probability >= 58:
            risk_score -= 8
            controls.append("Trap probability elevated; require extra confirmation.")

        if trend_probability >= 70 and expansion_probability >= 65 and ecosystem_score >= 70:
            risk_score += 15
            confirmations.append("Trend, expansion, and ecosystem alignment support deployment.")

        risk_score = max(0, min(100, risk_score))

        if blockers:
            regime = "liquidity_fragile"
            execution_posture = "block_aggressive"
        elif high_impact_count > 0:
            regime = "event_volatility"
            execution_posture = "event_risk_reduced"
        elif "pin" in dealer_regime:
            regime = "dealer_controlled"
            execution_posture = "range_controlled"
        elif risk_score >= 72 and trend_probability >= 65:
            regime = "trend_expansion"
            execution_posture = "controlled_deployment"
        elif risk_score >= 62:
            regime = "risk_on"
            execution_posture = "standard_deployment"
        elif risk_score <= 40:
            regime = "risk_off"
            execution_posture = "defensive_only"

        return {
            "risk_regime": regime,
            "risk_score": risk_score,
            "execution_posture": execution_posture,
            "allow_autonomy": risk_score >= 62 and not blockers,
            "allow_aggressive": risk_score >= 72 and not blockers,
            "blockers": blockers[:6],
            "controls": controls[:6],
            "confirmations": confirmations[:6],
        }
