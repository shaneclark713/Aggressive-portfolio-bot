from __future__ import annotations

from typing import Any

from services.ai_consensus_engine import AIConsensusEngine


class InstitutionalAIEcosystemEngine:
    """Institutional AI ecosystem coordinator with multi-agent consensus."""

    def __init__(self):
        self.consensus_engine = AIConsensusEngine()

    def build(self, payload: dict[str, Any]) -> dict[str, Any]:
        consensus = self.consensus_engine.evaluate(payload)
        memory = payload.get("trade_memory", {}) or {}
        review = payload.get("ai_review", {}) or {}
        flow = payload.get("institutional_flow", {}) or {}
        theta = payload.get("theta_protection", {}) or {}
        mutation = payload.get("autonomous_mutation", {}) or {}
        personality = payload.get("session_personality", {}) or {}

        review_score = int(review.get("review_score", 50) or 50)
        autonomy_win_rate = int(memory.get("autonomy_win_rate", 50) or 50)
        consensus_score = int(consensus.get("consensus_score", 50) or 50)
        flow_quality = int(flow.get("expansion_quality_score", 50) or 50)
        theta_risk = int(theta.get("theta_risk_score", 50) or 50)

        ecosystem_score = 50
        ecosystem_score += int((consensus_score - 50) * 0.30)
        ecosystem_score += int((review_score - 50) * 0.25)
        ecosystem_score += int((autonomy_win_rate - 50) * 0.15)
        ecosystem_score += int((flow_quality - 50) * 0.15)
        ecosystem_score -= int((theta_risk - 50) * 0.15)
        ecosystem_score = max(0, min(100, ecosystem_score))

        return {
            "ecosystem_score": ecosystem_score,
            "ecosystem_label": "INSTITUTIONAL_ACTIVE" if ecosystem_score >= 70 else "BUILDING",
            "consensus": consensus,
            "environment_state": personality.get("environment_state"),
            "reinforcement_bias": memory.get("reinforcement_bias"),
            "adaptation_state": mutation.get("aggressiveness_shift", "stable"),
            "allow_aggressive": bool(consensus.get("allow_aggressive") and ecosystem_score >= 70),
            "deployment_mode": "autonomous_candidate" if ecosystem_score >= 75 else "advisory_only",
        }
