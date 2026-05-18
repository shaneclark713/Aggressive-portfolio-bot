from __future__ import annotations

from typing import Any


class TrapDetectionEngine:
    """Institutional liquidity trap and failed-move detection.

    Detects conditions associated with fake breakouts, liquidity sweeps,
    exhaustion extensions, and reversal instability.
    """

    def detect(
        self,
        probabilities: dict[str, Any],
        structure: dict[str, Any],
        session_personality: dict[str, Any],
        execution_timing: dict[str, Any],
        latest: float,
        vwap: float,
        rsi_5m: float,
    ) -> dict[str, Any]:
        trap_probability = int(probabilities.get("trap_probability") or 0)
        reversal_probability = int(probabilities.get("reversal_probability") or 0)
        mean_reversion = int(probabilities.get("mean_reversion_probability") or 0)
        expansion_probability = int(probabilities.get("gamma_expansion_probability") or 0)

        personality = str(session_personality.get("personality") or "balanced")
        timing_quality = str(execution_timing.get("execution_quality") or "mixed")
        structure_bias = str(structure.get("bias") or "balanced")

        danger_score = 25
        trap_type = "no dominant trap structure"
        confirmation_required = False

        warnings: list[str] = []
        defenses: list[str] = []

        if trap_probability >= 60:
            danger_score += 25
            confirmation_required = True
            trap_type = "liquidity sweep risk"
            warnings.append("Liquidity sweep probability elevated.")

        if reversal_probability >= 60:
            danger_score += 15
            trap_type = "failed breakout reversal risk"
            warnings.append("Reversal probability elevated after extension.")

        if mean_reversion >= 65:
            danger_score += 12
            warnings.append("Dealer-controlled rotation may suppress continuation.")

        if expansion_probability >= 65 and rsi_5m >= 72:
            danger_score += 15
            trap_type = "exhaustion breakout risk"
            warnings.append("Momentum extension risk elevated during expansion conditions.")

        if latest < vwap and "upside" in structure_bias:
            danger_score += 12
            trap_type = "failed continuation risk"
            warnings.append("Upside structure weakening below VWAP.")

        if "gamma pin" in personality.lower():
            danger_score += 15
            confirmation_required = True
            warnings.append("Gamma pin personality increases fake breakout probability.")

        if "poor" in timing_quality:
            danger_score += 10
            warnings.append("Execution timing deterioration increases instability risk.")

        if rsi_5m >= 78:
            danger_score += 12
            warnings.append("RSI extension reaching exhaustion territory.")

        danger_score = max(5, min(95, danger_score))

        if danger_score >= 75:
            severity = "high trap danger"
        elif danger_score >= 55:
            severity = "elevated trap risk"
        elif danger_score <= 30:
            severity = "stable continuation environment"
        else:
            severity = "moderate tactical instability"

        defenses.extend([
            "Require breakout confirmation before entry.",
            "Avoid chasing extension candles.",
            "Use tighter stops during instability.",
        ])

        return {
            "severity": severity,
            "danger_score": danger_score,
            "trap_type": trap_type,
            "confirmation_required": confirmation_required,
            "warnings": warnings[:6] or ["No abnormal trap behavior detected."],
            "defenses": defenses[:6],
        }
