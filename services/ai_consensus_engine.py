from __future__ import annotations

from typing import Any


class AIConsensusEngine:
    """Institutional multi-agent consensus layer."""

    def evaluate(self, payload: dict[str, Any]) -> dict[str, Any]:
        review = payload.get('ai_review', {}) or {}
        flow = payload.get('institutional_flow', {}) or {}
        theta = payload.get('theta_protection', {}) or {}
        trap = payload.get('trap_detection', {}) or {}
        probabilities = payload.get('probabilities', {}) or {}

        agents = {
            'risk_agent': max(0,100-int(theta.get('theta_risk_score',50))),
            'flow_agent': int(flow.get('expansion_quality_score',50)),
            'theta_agent': int(theta.get('premium_hold_score',50)),
            'momentum_agent': int(probabilities.get('trend_probability',50)),
            'trap_agent': max(0,100-int(probabilities.get('trap_probability',50))),
        }

        values=list(agents.values())
        consensus_score=int(sum(values)/len(values))
        disagreement=max(values)-min(values)

        return {
            'consensus_score': consensus_score,
            'consensus_label':'ALIGNED' if disagreement<25 else 'CONFLICTED',
            'disagreement_score': disagreement,
            'allow_aggressive': consensus_score>=70 and disagreement<25,
            'agents': agents,
        }
