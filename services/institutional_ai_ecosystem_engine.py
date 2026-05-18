from __future__ import annotations

from typing import Any

from services.ai_consensus_engine import AIConsensusEngine
from services.risk_regime_engine import RiskRegimeEngine
from services.execution_feedback_engine import ExecutionFeedbackEngine
from services.runtime_health_engine import RuntimeHealthEngine


class InstitutionalAIEcosystemEngine:
    """Institutional AI ecosystem coordinator with consensus, risk, feedback and runtime health."""

    def __init__(self):
        self.consensus_engine = AIConsensusEngine()
        self.risk_regime_engine = RiskRegimeEngine()
        self.execution_feedback_engine = ExecutionFeedbackEngine()
        self.runtime_health_engine = RuntimeHealthEngine()

    def build(self, payload: dict[str, Any]) -> dict[str, Any]:
        consensus = self.consensus_engine.evaluate(payload)
        execution_feedback = self.execution_feedback_engine.evaluate(payload)
        runtime_health = self.runtime_health_engine.evaluate(payload)
        risk_regime = self.risk_regime_engine.classify({**payload, "ecosystem": {"ecosystem_score": 50}})

        memory = payload.get("trade_memory", {}) or {}
        review = payload.get("ai_review", {}) or {}
        flow = payload.get("institutional_flow", {}) or {}
        theta = payload.get("theta_protection", {}) or {}
        mutation = payload.get("autonomous_mutation", {}) or {}
        personality = payload.get("session_personality", {}) or {}

        ecosystem_score = 50
        ecosystem_score += int((int(consensus.get("consensus_score", 50)) - 50) * 0.22)
        ecosystem_score += int((int(review.get("review_score", 50)) - 50) * 0.18)
        ecosystem_score += int((int(memory.get("autonomy_win_rate", 50)) - 50) * 0.10)
        ecosystem_score += int((int(flow.get("expansion_quality_score", 50)) - 50) * 0.10)
        ecosystem_score += int((int(execution_feedback.get("execution_score", 50)) - 50) * 0.18)
        ecosystem_score += int((int(runtime_health.get("runtime_score", 100)) - 75) * 0.12)
        ecosystem_score -= int((int(theta.get("theta_risk_score", 50)) - 50) * 0.15)

        if not risk_regime.get("allow_aggressive"):
            ecosystem_score -= 10
        if not runtime_health.get("allow_autonomy"):
            ecosystem_score -= 15

        ecosystem_score = max(0, min(100, ecosystem_score))
        deployment_mode = "autonomous_candidate" if ecosystem_score >= 75 and risk_regime.get("allow_autonomy") and runtime_health.get("allow_autonomy") else "advisory_only"

        return {
            "ecosystem_score": ecosystem_score,
            "ecosystem_label": "INSTITUTIONAL_ACTIVE" if ecosystem_score >= 70 else "BUILDING",
            "consensus": consensus,
            "risk_regime": risk_regime,
            "execution_feedback": execution_feedback,
            "runtime_health": runtime_health,
            "feedback_adaptation": execution_feedback.get("adaptation_signal", "maintain"),
            "environment_state": personality.get("environment_state"),
            "reinforcement_bias": memory.get("reinforcement_bias"),
            "adaptation_state": mutation.get("aggressiveness_shift", "stable"),
            "allow_aggressive": bool(
                consensus.get("allow_aggressive")
                and risk_regime.get("allow_aggressive")
                and runtime_health.get("runtime_mode") == "normal"
                and ecosystem_score >= 70
            ),
            "deployment_mode": deployment_mode,
        }
