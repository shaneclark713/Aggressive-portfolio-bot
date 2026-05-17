from __future__ import annotations

from typing import Any


class Phase8ReinforcementEngine:
    """Adaptive reinforcement propagation layer."""

    def propagate(self, phase8: dict[str, Any], trade_memory: dict[str, Any]) -> dict[str, Any]:
        review = phase8.get('ai_review', {})
        mutation = phase8.get('autonomous_mutation', {})

        review_score = int(review.get('review_score') or 50)
        adaptation = int(mutation.get('adaptation_score') or 50)

        reinforcement = max(5, min(95, int((review_score + adaptation) / 2)))

        return {
            'reinforcement_score': reinforcement,
            'reinforcement_bias': 'aggressive' if reinforcement >= 70 else 'defensive' if reinforcement <= 40 else 'balanced',
            'memory_alignment': trade_memory.get('reinforcement_bias', 'neutral'),
            'phase9_ready': reinforcement >= 70,
        }
