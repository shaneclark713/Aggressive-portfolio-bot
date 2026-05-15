from __future__ import annotations

from typing import Any


class SessionPersonalityEngine:
    """Institutional market-session personality classifier.

    Determines dominant intraday market behavior so the execution stack can
    adapt its tactics automatically.
    """

    def classify(
        self,
        probabilities: dict[str, Any],
        structure: dict[str, Any],
        dealer_gamma: dict[str, Any],
        execution_timing: dict[str, Any],
        latest: float,
        vwap: float,
        rsi_5m: float,
    ) -> dict[str, Any]:
        trend_probability = int(probabilities.get("trend_probability") or 0)
        mean_reversion = int(probabilities.get("mean_reversion_probability") or 0)
        reversal_probability = int(probabilities.get("reversal_probability") or 0)
        trap_probability = int(probabilities.get("trap_probability") or 0)
        expansion_probability = int(probabilities.get("gamma_expansion_probability") or 0)

        dealer_regime = str(dealer_gamma.get("dealer_regime") or "balanced")
        timing_quality = str(execution_timing.get("execution_quality") or "mixed")
        structure_bias = str(structure.get("bias") or "balanced")

        personality = "balanced rotational session"
        aggression = "moderate"
        execution_style = "balanced tactical execution"

        notes: list[str] = []
        warnings: list[str] = []

        if trend_probability >= 70 and expansion_probability >= 60:
            personality = "trend expansion session"
            aggression = "high"
            execution_style = "continuation breakout execution"
            notes.append("Trend and expansion probabilities support continuation behavior.")

        elif mean_reversion >= 65 or "pin risk" in dealer_regime:
            personality = "gamma pin rotational session"
            aggression = "low"
            execution_style = "range-based rotational execution"
            warnings.append("Dealer pinning behavior may suppress continuation moves.")

        elif reversal_probability >= 60 and trap_probability >= 50:
            personality = "failed breakout reversal session"
            aggression = "moderate"
            execution_style = "reversal / fade execution"
            warnings.append("Failed breakout conditions may produce sharp reversals.")

        elif trap_probability >= 65:
            personality = "liquidity trap session"
            aggression = "defensive"
            execution_style = "confirmation-only execution"
            warnings.append("Liquidity sweeps and fake breakouts likely elevated.")

        elif expansion_probability >= 65:
            personality = "high-volatility expansion session"
            aggression = "high"
            execution_style = "volatility expansion execution"
            notes.append("Expansion environment may reward momentum continuation.")

        if latest > vwap and "upside" in structure_bias:
            notes.append("Buy-side control remains stronger while above VWAP.")

        elif latest < vwap:
            warnings.append("Sell-side control increases reversal risk below VWAP.")

        if rsi_5m >= 75:
            warnings.append("Momentum extension risk elevated after strong directional move.")

        if "poor" in timing_quality:
            aggression = "reduced"
            warnings.append("Execution timing quality deteriorating.")

        confidence = self._confidence(
            trend_probability,
            mean_reversion,
            reversal_probability,
            trap_probability,
            expansion_probability,
        )

        return {
            "personality": personality,
            "confidence": confidence,
            "aggression": aggression,
            "execution_style": execution_style,
            "notes": notes[:6],
            "warnings": warnings[:6] or ["No abnormal session warning detected."],
        }

    def _confidence(
        self,
        trend: int,
        mean_reversion: int,
        reversal: int,
        trap: int,
        expansion: int,
    ) -> int:
        values = [trend, mean_reversion, reversal, trap, expansion]
        strongest = max(values)
        weakest = min(values)
        confidence = 50 + int((strongest - weakest) * 0.45)
        return max(5, min(95, confidence))
