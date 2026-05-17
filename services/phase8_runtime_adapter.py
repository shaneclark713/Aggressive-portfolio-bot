from __future__ import annotations

from services.phase8_adaptive_orchestrator import Phase8AdaptiveOrchestrator
from services.phase8_reinforcement_engine import Phase8ReinforcementEngine
from services.phase9_readiness_controller import Phase9ReadinessController


class Phase8RuntimeAdapter:
    """Temporary integration layer before direct Spy0DteService merge."""

    def __init__(self):
        self.phase8 = Phase8AdaptiveOrchestrator()
        self.reinforcement = Phase8ReinforcementEngine()
        self.phase9 = Phase9ReadinessController()
