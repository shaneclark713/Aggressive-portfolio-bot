from __future__ import annotations

from typing import Any


class AutonomousMutationEngine:
    """Adaptive self-adjustment intelligence.

    Produces tactical mutation recommendations based on recurring execution
    quality, theta protection stress, flow alignment, and trap behavior.
    """

    def mutate(
        self,
        ai_review: dict[str, Any],
        probabilities: dict[str, Any],
        execution_timing: dict[str, Any],
        theta_protection: dict[str, Any],
        institutional_flow: dict[str, Any],
        trap_detection: dict[str, Any],
    ) -> dict[str, Any]:
        review_score = int(ai_review.get("review_score") or 50)
        trend_probability = int(probabilities.get("trend_probability") or 0)
        trap_probability = int(probabilities.get("trap_probability") or 0)
        timing_score = int(execution_timing.get("timing_score") or 50)
        theta_risk = int(theta_protection.get("theta_risk_score") or 50)
        flow_quality = int(institutional_flow.get("expansion_quality_score") or 50)

        mutation_bias = "stable"
        aggressiveness_shift = "unchanged"
        mutation_actions: list[str] = []
        safeguards: list[str] = []

        adaptation_score = 50
        adaptation_score += int((review_score - 50) * 0.35)
        adaptation_score += int((flow_quality - 50) * 0.25)
        adaptation_score += int((timing_score - 50) * 0.20)

        adaptation_score -= int((theta_risk - 50) * 0.30)
        adaptation_score -= int((trap_probability - 50) * 0.35)

        if review_score >= 75 and trend_probability >= 65:
            mutation_bias = "controlled_aggression"
            aggressiveness_shift = "slightly_increase"
            mutation_actions.append("Allow controlled increase in continuation exposure after confirmation stacking.")

        if theta_risk >= 70:
            mutation_bias = "premium_defense"
            aggressiveness_shift = "reduce"
            mutation_actions.append("Reduce exposure duration and tighten premium protection thresholds.")
            safeguards.append("Block overexposure during high theta compression windows.")

        if trap_probability >= 65:
            mutation_bias = "confirmation_priority"
            mutation_actions.append("Increase confirmation requirements before breakout participation.")
            safeguards.append("Require stronger liquidity validation before scaling entries.")

        if flow_quality >= 72 and review_score >= 72:
            mutation_actions.append("Institutional flow alignment permits measured runner expansion.")

        if timing_score <= 35:
            safeguards.append("Disable aggressive scaling during poor execution windows.")

        if adaptation_score <= 40:
            aggressiveness_shift = "decrease"
            safeguards.append("Favor capital preservation over expansion attempts.")

        adaptation_score = max(5, min(95, int(adaptation_score)))

        return {
            "adaptation_score": adaptation_score,
            "mutation_bias": mutation_bias,
            "aggressiveness_shift": aggressiveness_shift,
            "self_adjustment_active": adaptation_score >= 55,
            "mutation_actions": mutation_actions[:6] or ["Maintain current adaptive framework without major mutation."],
            "safeguards": safeguards[:6] or ["Standard institutional risk controls remain active."],
        }
