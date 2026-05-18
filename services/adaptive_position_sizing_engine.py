from __future__ import annotations

from typing import Any


class AdaptivePositionSizingEngine:
    """Adaptive institutional position sizing engine."""

    def calculate(
        self,
        probabilities: dict[str, Any],
        session_personality: dict[str, Any],
        trap_detection: dict[str, Any],
        trade_memory: dict[str, Any],
        execution_timing: dict[str, Any],
        adaptive_exits: dict[str, Any],
    ) -> dict[str, Any]:
        trend_probability = int(probabilities.get("trend_probability") or 0)
        trap_probability = int(probabilities.get("trap_probability") or 0)
        runner_probability = int(probabilities.get("runner_probability") or 0)

        personality = str(session_personality.get("personality") or "balanced")
        aggression = str(session_personality.get("aggression") or "moderate")
        timing_quality = str(execution_timing.get("execution_quality") or "mixed")

        memory_adjustment = int(trade_memory.get("confidence_adjustment") or 0)
        hold_strength = int(adaptive_exits.get("hold_strength") or 50)
        danger_score = int(trap_detection.get("danger_score") or 0)

        base_size = 1.0
        conviction_score = 50

        notes: list[str] = []
        protections: list[str] = []

        if trend_probability >= 70:
            base_size += 0.35
            conviction_score += 12
            notes.append("Trend continuation probabilities support increased exposure.")

        if runner_probability >= 60:
            base_size += 0.15
            conviction_score += 6
            notes.append("Runner conditions support maintaining larger exposure.")

        if trap_probability >= 55 or danger_score >= 65:
            base_size -= 0.45
            conviction_score -= 18
            protections.append("Trap conditions require defensive position reduction.")

        if "trend expansion" in personality.lower():
            base_size += 0.20
            conviction_score += 8

        elif "gamma pin" in personality.lower():
            base_size -= 0.30
            conviction_score -= 10
            protections.append("Gamma pin environment suppresses conviction sizing.")

        if "high" in aggression:
            base_size += 0.10

        elif "defensive" in aggression or "reduced" in aggression:
            base_size -= 0.20

        if "high-quality" in timing_quality:
            base_size += 0.10
            conviction_score += 5

        elif "poor" in timing_quality:
            base_size -= 0.25
            conviction_score -= 8
            protections.append("Poor timing quality reduces sizing allowance.")

        if memory_adjustment > 0:
            base_size += min(memory_adjustment / 100, 0.15)
            conviction_score += memory_adjustment
            notes.append("Historical environment performance increases conviction.")

        elif memory_adjustment < 0:
            base_size -= min(abs(memory_adjustment) / 100, 0.20)
            conviction_score += memory_adjustment
            protections.append("Historical weakness reduces exposure.")

        if hold_strength <= 35:
            base_size -= 0.15
            protections.append("Weak continuation quality lowers optimal sizing.")

        size_pct = max(0.10, min(2.00, round(base_size, 2)))
        conviction_score = max(5, min(95, conviction_score))

        if size_pct >= 1.5:
            sizing_label = "aggressive institutional sizing"
        elif size_pct >= 1.1:
            sizing_label = "expanded conviction sizing"
        elif size_pct <= 0.6:
            sizing_label = "defensive reduced sizing"
        else:
            sizing_label = "balanced tactical sizing"

        if not protections:
            protections.append("No abnormal sizing suppression triggered.")

        return {
            "size_multiplier": size_pct,
            "conviction_score": conviction_score,
            "sizing_label": sizing_label,
            "notes": notes[:6],
            "protections": protections[:6],
        }
