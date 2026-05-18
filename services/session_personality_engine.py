from __future__ import annotations

from typing import Any


class SessionPersonalityEngine:
    """Institutional market-session personality classifier with Phase 9 environment states."""

    def classify(self, probabilities: dict[str, Any], structure: dict[str, Any], dealer_gamma: dict[str, Any], execution_timing: dict[str, Any], latest: float, vwap: float, rsi_5m: float,) -> dict[str, Any]:
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
        environment_state = "balanced_rotation"
        notes=[]; warnings=[]

        if trend_probability >= 75 and expansion_probability >= 65:
            personality="trend expansion session"; aggression="high"; execution_style="continuation breakout execution"
            environment_state="trend_acceleration"
            notes.append("Trend acceleration environment detected.")
        elif mean_reversion >=65 or "pin risk" in dealer_regime:
            personality="gamma pin rotational session"; aggression="low"; execution_style="range-based rotational execution"
            environment_state="gamma_pin"
            warnings.append("Gamma pin environment suppressing continuation.")
        elif trap_probability>=65:
            personality="liquidity trap session"; aggression="defensive"; execution_style="confirmation-only execution"
            environment_state="trap_expansion"
        elif expansion_probability>=65 and rsi_5m<70:
            environment_state="institutional_continuation"
        elif reversal_probability>=60 and latest<vwap:
            environment_state="theta_compression"

        confidence=self._confidence(trend_probability,mean_reversion,reversal_probability,trap_probability,expansion_probability)
        return {"personality":personality,"confidence":confidence,"aggression":aggression,"execution_style":execution_style,"environment_state":environment_state,"notes":notes[:6],"warnings":warnings[:6] or ["No abnormal session warning detected."]}

    def _confidence(self,trend:int,mean_reversion:int,reversal:int,trap:int,expansion:int)->int:
        values=[trend,mean_reversion,reversal,trap,expansion]
        return max(5,min(95,50+int((max(values)-min(values))*0.45)))