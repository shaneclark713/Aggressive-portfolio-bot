from __future__ import annotations

from typing import Any

from services.ai_trade_review_engine import AITradeReviewEngine
from services.autonomous_mutation_engine import AutonomousMutationEngine
from services.institutional_flow_expansion_engine import InstitutionalFlowExpansionEngine
from services.theta_decay_protection_engine import ThetaDecayProtectionEngine


class Phase8AdaptiveOrchestrator:
    """Phase 8 orchestration layer.

    Coordinates remaining Phase 8 engines and produces a unified adaptive
    intelligence payload before Phase 9 autonomy expansion.
    """

    def __init__(self):
        self.theta = ThetaDecayProtectionEngine()
        self.flow = InstitutionalFlowExpansionEngine()
        self.review = AITradeReviewEngine()
        self.mutation = AutonomousMutationEngine()

    def execute(
        self,
        probabilities: dict[str, Any],
        execution_timing: dict[str, Any],
        adaptive_exits: dict[str, Any],
        autonomous_scaling: dict[str, Any],
        session_personality: dict[str, Any],
        trap_detection: dict[str, Any],
        trade_memory: dict[str, Any],
        dealer_gamma: dict[str, Any],
        cross_market: dict[str, Any],
        narrative: dict[str, Any],
        playbook: dict[str, Any],
        latest: float,
        vwap: float,
        rsi_5m: float,
    ) -> dict[str, Any]:
        theta = self.theta.evaluate(
            probabilities, execution_timing, adaptive_exits,
            autonomous_scaling, session_personality,
            trap_detection, rsi_5m, latest, vwap,
        )

        flow = self.flow.evaluate(
            dealer_gamma, cross_market, probabilities,
            narrative, execution_timing, session_personality,
            trap_detection, latest, vwap, rsi_5m,
        )

        review = self.review.review(
            playbook, probabilities, execution_timing,
            adaptive_exits, theta, flow,
            trap_detection, trade_memory,
        )

        mutation = self.mutation.mutate(
            review, probabilities, execution_timing,
            theta, flow, trap_detection,
        )

        return {
            'theta_protection': theta,
            'institutional_flow': flow,
            'ai_review': review,
            'autonomous_mutation': mutation,
            'phase8_alignment_score': int((review['review_score'] + flow['expansion_quality_score']) / 2),
            'phase9_ready': review['review_score'] >= 70 and mutation['self_adjustment_active'],
        }
