from __future__ import annotations

from typing import Any


class AdaptiveExitEngine:
    """Institutional adaptive exit intelligence.

    Controls runner behavior, trailing logic, continuation probability,
    and profit-protection decisions.
    """

    def evaluate(
        self,
        probabilities: dict[str, Any],
        playbook: dict[str, Any],
        structure: dict[str, Any],
        execution_timing: dict[str, Any],
        rsi_5m: float,
        latest: float,
        vwap: float,
    ) -> dict[str, Any]:
        trend_probability = int(probabilities.get("trend_probability") or 0)
        runner_probability = int(probabilities.get("runner_probability") or 0)
        trap_probability = int(probabilities.get("trap_probability") or 0)
        expansion_probability = int(probabilities.get("gamma_expansion_probability") or 0)

        playbook_name = str(playbook.get("playbook") or "Adaptive Tactical")
        execution_quality = str(execution_timing.get("execution_quality") or "mixed")
        structure_bias = str(structure.get("bias") or "balanced")

        hold_strength = 50
        runner_allowed = False
        scaling_mode = "standard"
        trailing_mode = "tight"
        exit_aggression = "balanced"

        notes: list[str] = []
        protections: list[str] = []

        if trend_probability >= 65:
            hold_strength += 18
            notes.append("Trend continuation probability supports holding winners longer.")

        if runner_probability >= 55:
            runner_allowed = True
            hold_strength += 12
            trailing_mode = "adaptive"
            notes.append("Runner conditions improving after confirmation stacking.")

        if expansion_probability >= 60:
            scaling_mode = "expansion"
            hold_strength += 10
            notes.append("Gamma expansion probability supports staggered exits.")

        if trap_probability >= 55:
            hold_strength -= 18
            trailing_mode = "tight"
            protections.append("Trap probability elevated; tighten stops aggressively.")

        if rsi_5m >= 72:
            hold_strength -= 10
            exit_aggression = "aggressive_profit_protection"
            protections.append("RSI stretched; protect gains into extension.")

        if latest > vwap and "upside" in structure_bias:
            hold_strength += 8
            notes.append("Price above VWAP keeps buy-side control intact.")

        elif latest < vwap:
            hold_strength -= 12
            protections.append("Price below VWAP weakens continuation quality.")

        if "high-quality" in execution_quality:
            hold_strength += 10
            notes.append("Execution timing quality remains favorable.")

        elif "poor" in execution_quality:
            hold_strength -= 15
            protections.append("Execution conditions deteriorating; reduce runner exposure.")

        if "Gamma Pin" in playbook_name:
            runner_allowed = False
            scaling_mode = "quick_scalp"
            hold_strength -= 10
            protections.append("Gamma pin conditions favor faster exits.")

        if "Failed Breakout" in playbook_name:
            trailing_mode = "tight"
            exit_aggression = "fast"
            protections.append("Failed breakout environment requires defensive exits.")

        hold_strength = max(5, min(95, hold_strength))

        if hold_strength >= 75:
            exit_style = "institutional runner management"
        elif hold_strength >= 60:
            exit_style = "measured continuation holding"
        elif hold_strength <= 35:
            exit_style = "rapid profit protection"
        else:
            exit_style = "balanced tactical exits"

        if not protections:
            protections.append("No abnormal exit risk beyond standard 0DTE volatility.")

        return {
            "exit_style": exit_style,
            "hold_strength": hold_strength,
            "runner_allowed": runner_allowed,
            "scaling_mode": scaling_mode,
            "trailing_mode": trailing_mode,
            "exit_aggression": exit_aggression,
            "notes": notes[:6],
            "protections": protections[:6],
        }
