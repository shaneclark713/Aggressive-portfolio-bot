from __future__ import annotations

from typing import Any


class Phase9ReadinessController:

    def evaluate(self, phase8: dict[str, Any], reinforcement: dict[str, Any]) -> dict[str, Any]:
        alignment = int(phase8.get('phase8_alignment_score') or 50)
        reinforcement_score = int(reinforcement.get('reinforcement_score') or 50)

        score = max(5, min(95, int((alignment + reinforcement_score)/2)))

        return {
            'phase9_score': score,
            'ready_for_phase9': score >= 72,
            'execution_mode': 'adaptive_autonomy' if score >=72 else 'institutional_guided'
        }
