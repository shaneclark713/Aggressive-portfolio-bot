from __future__ import annotations

from collections import defaultdict
from typing import Any


class TradeMemoryEngine:
    """Adaptive trade memory and environment learning engine.

    Maintains lightweight in-memory performance tracking for tactical
    environments, playbooks, and session personalities.
    """

    def __init__(self):
        self.playbook_stats: dict[str, dict[str, int]] = defaultdict(
            lambda: {"wins": 0, "losses": 0}
        )

        self.personality_stats: dict[str, dict[str, int]] = defaultdict(
            lambda: {"wins": 0, "losses": 0}
        )

        self.environment_stats: dict[str, dict[str, int]] = defaultdict(
            lambda: {"wins": 0, "losses": 0}
        )

    def snapshot(
        self,
        playbook: dict[str, Any],
        session_personality: dict[str, Any],
        trap_detection: dict[str, Any],
        probabilities: dict[str, Any],
    ) -> dict[str, Any]:
        playbook_name = str(playbook.get("playbook") or "Adaptive Tactical")
        personality = str(session_personality.get("personality") or "balanced")
        trap_type = str(trap_detection.get("trap_type") or "stable")

        trend_probability = int(probabilities.get("trend_probability") or 0)
        trap_probability = int(probabilities.get("trap_probability") or 0)

        environment_key = (
            f"trend_{trend_probability // 10}_"
            f"trap_{trap_probability // 10}_"
            f"{trap_type.lower().replace(' ', '_')}"
        )

        playbook_wr = self._win_rate(self.playbook_stats[playbook_name])
        personality_wr = self._win_rate(self.personality_stats[personality])
        environment_wr = self._win_rate(self.environment_stats[environment_key])

        confidence_adjustment = 0

        if playbook_wr >= 60:
            confidence_adjustment += 5

        if personality_wr >= 60:
            confidence_adjustment += 5

        if environment_wr >= 65:
            confidence_adjustment += 8

        if environment_wr <= 35 and environment_wr > 0:
            confidence_adjustment -= 8

        notes: list[str] = []

        if confidence_adjustment > 0:
            notes.append("Historical environment performance supports tactical confidence.")

        elif confidence_adjustment < 0:
            notes.append("Historical environment weakness reduces confidence.")

        else:
            notes.append("Insufficient historical memory edge detected yet.")

        return {
            "playbook_win_rate": playbook_wr,
            "personality_win_rate": personality_wr,
            "environment_win_rate": environment_wr,
            "confidence_adjustment": confidence_adjustment,
            "notes": notes[:4],
            "environment_key": environment_key,
        }

    def record_trade(
        self,
        playbook_name: str,
        personality: str,
        environment_key: str,
        outcome: str,
    ) -> None:
        outcome_key = "wins" if outcome.lower() == "win" else "losses"

        self.playbook_stats[playbook_name][outcome_key] += 1
        self.personality_stats[personality][outcome_key] += 1
        self.environment_stats[environment_key][outcome_key] += 1

    def _win_rate(self, stats: dict[str, int]) -> int:
        wins = int(stats.get("wins") or 0)
        losses = int(stats.get("losses") or 0)
        total = wins + losses

        if total <= 0:
            return 0

        return int((wins / total) * 100)
