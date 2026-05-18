from __future__ import annotations

from collections import deque
from typing import Any


class EcosystemStateEngine:
    """Rolling ecosystem state persistence and restart recovery layer."""

    def __init__(self, max_history: int = 100):
        self.history = deque(maxlen=max_history)
        self.last_state: dict[str, Any] = {}

    def persist(self, payload: dict[str, Any]) -> dict[str, Any]:
        snapshot = {
            "ecosystem_score": payload.get("ecosystem_score"),
            "environment_state": payload.get("environment_state"),
            "deployment_mode": payload.get("deployment_mode"),
            "reinforcement_bias": payload.get("reinforcement_bias"),
            "adaptation_state": payload.get("adaptation_state"),
        }

        self.history.append(snapshot)
        self.last_state = snapshot

        return {
            "history_size": len(self.history),
            "restart_recovery_ready": len(self.history) > 0,
            "last_state": self.last_state,
        }

    def recover(self) -> dict[str, Any]:
        return {
            "restored": bool(self.last_state),
            "state": self.last_state,
            "history_size": len(self.history),
        }
