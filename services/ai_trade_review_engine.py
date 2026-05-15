from __future__ import annotations

from typing import Any


class AITradeReviewEngine:
    """Self-review intelligence layer.

    Reviews tactical quality, execution alignment, risk discipline, and
    institutional confirmation stacking after each analysis cycle.
    """

    def review(
        self,
        playbook: dict[str, Any],
        probabilities: dict[str, Any],
        execution_timing: dict[str, Any],
        adaptive_exits: dict[str, Any],
        theta_protection: dict[str, Any],
        institutional_flow: dict[str, Any],
        trap_detection: dict[str, Any],
        trade_memory: dict[str, Any],
    ) -> dict[str, Any]:
        playbook_name = str(playbook.get("playbook") or "Adaptive Tactical")
        execution_quality = str(execution_timing.get("execution_quality") or "mixed")
        protection_mode = str(theta_protection.get("protection_mode") or "balanced")
        expansion_state = str(institutional_flow.get("expansion_state") or "mixed")

        trend_probability = int(probabilities.get("trend_probability") or 0)
        trap_probability = int(probabilities.get("trap_probability") or 0)
        timing_score = int(execution_timing.get("timing_score") or 50)
        hold_strength = int(adaptive_exits.get("hold_strength") or 50)
        theta_risk = int(theta_protection.get("theta_risk_score") or 50)
        flow_quality = int(institutional_flow.get("expansion_quality_score") or 50)

        review_score = 50
        strengths: list[str] = []
        weaknesses: list[str] = []
        corrections: list[str] = []

        review_score += int((trend_probability - 50) * 0.30)
        review_score += int((timing_score - 50) * 0.25)
        review_score += int((hold_strength - 50) * 0.20)
        review_score += int((flow_quality - 50) * 0.25)

        review_score -= int((trap_probability - 50) * 0.35)
        review_score -= int((theta_risk - 50) * 0.25)

        if "high-quality" in execution_quality:
            review_score += 10
            strengths.append("Execution timing aligned with institutional expansion conditions.")

        if "poor" in execution_quality:
            review_score -= 12
            weaknesses.append("Execution timing quality degraded.")

        if "acceleration" in expansion_state:
            review_score += 12
            strengths.append("Institutional participation confirmed directional continuation.")

        if "suppressed" in expansion_state:
            review_score -= 12
            weaknesses.append("Expansion environment failed to support momentum continuation.")

        if "critical" in protection_mode:
            review_score -= 15
            corrections.append("Reduce hold time and increase premium protection during elevated theta conditions.")

        if trap_probability >= 60:
            weaknesses.append("Trap probability was elevated before execution confirmation.")
            corrections.append("Require additional confirmation stacking before aggressive entries.")

        if trend_probability >= 68 and flow_quality >= 65:
            strengths.append("Trend and institutional flow aligned correctly.")

        if hold_strength <= 40:
            corrections.append("Profit protection logic should override runner bias faster.")

        if "Gamma Pin" in playbook_name:
            corrections.append("Avoid overholding during gamma suppression environments.")

        memory_bias = trade_memory.get("reinforcement_bias") or trade_memory.get("memory_bias")
        if memory_bias:
            strengths.append(f"Trade memory reinforcement bias: {memory_bias}.")

        review_score = max(5, min(95, int(review_score)))

        return {
            "review_score": review_score,
            "review_grade": self._grade(review_score),
            "execution_alignment": review_score >= 65,
            "strengths": strengths[:6],
            "weaknesses": weaknesses[:6] or ["No major tactical weakness detected."],
            "corrections": corrections[:6] or ["Maintain current tactical discipline and confirmation structure."],
        }

    def _grade(self, score: int) -> str:
        if score >= 85:
            return "institutional-grade alignment"
        if score >= 70:
            return "high-quality tactical execution"
        if score >= 55:
            return "constructive but mixed"
        if score >= 40:
            return "defensive execution quality"
        return "poor tactical alignment"
