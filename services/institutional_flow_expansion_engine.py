from __future__ import annotations

from typing import Any


class InstitutionalFlowExpansionEngine:
    """Institutional flow expansion intelligence.

    Expands dealer-gamma analysis into broader institutional participation,
    liquidity pressure, momentum sponsorship, and expansion-quality scoring.
    """

    def evaluate(
        self,
        dealer_gamma: dict[str, Any],
        cross_market: dict[str, Any],
        probabilities: dict[str, Any],
        narrative: dict[str, Any],
        execution_timing: dict[str, Any],
        session_personality: dict[str, Any],
        trap_detection: dict[str, Any],
        latest: float,
        vwap: float,
        rsi_5m: float,
    ) -> dict[str, Any]:
        dealer_regime = str(dealer_gamma.get("dealer_regime") or "neutral")
        cross_tone = str(cross_market.get("tone") or "neutral")
        narrative_bias = str(narrative.get("bias") or narrative.get("narrative") or "balanced")
        execution_quality = str(execution_timing.get("execution_quality") or "mixed")
        personality = str(session_personality.get("session_personality") or session_personality.get("personality") or "balanced")
        trap_risk = str(trap_detection.get("trap_risk") or trap_detection.get("risk_level") or "normal")

        trend_probability = int(probabilities.get("trend_probability") or 0)
        expansion_probability = int(probabilities.get("gamma_expansion_probability") or 0)
        trap_probability = int(probabilities.get("trap_probability") or 0)
        runner_probability = int(probabilities.get("runner_probability") or 0)

        sponsorship_score = 45
        liquidity_pressure = 40
        expansion_quality = 45

        notes: list[str] = []
        warnings: list[str] = []
        confirmations: list[str] = []

        if "call-heavy" in dealer_regime or "chase" in dealer_regime:
            sponsorship_score += 18
            liquidity_pressure += 15
            confirmations.append("Dealer positioning supports upside continuation pressure.")

        if "put-heavy" in dealer_regime or "hedge" in dealer_regime:
            sponsorship_score += 8
            liquidity_pressure += 18
            warnings.append("Defensive dealer hedging can accelerate downside expansion.")

        if "pin" in dealer_regime:
            expansion_quality -= 18
            liquidity_pressure -= 10
            warnings.append("Dealer pinning environment suppresses clean directional expansion.")

        if "risk-on" in cross_tone:
            sponsorship_score += 12
            expansion_quality += 10
            confirmations.append("Cross-market tone supports institutional risk participation.")

        if "risk-off" in cross_tone or "defensive" in cross_tone:
            expansion_quality -= 10
            warnings.append("Cross-market tone weakens continuation reliability.")

        sponsorship_score += int((trend_probability - 50) * 0.35)
        expansion_quality += int((expansion_probability - 50) * 0.40)
        expansion_quality += int((runner_probability - 50) * 0.25)
        expansion_quality -= int((trap_probability - 50) * 0.35)

        if latest > vwap:
            sponsorship_score += 8
            confirmations.append("Price holding above VWAP confirms stronger institutional sponsorship.")
        else:
            expansion_quality -= 8
            warnings.append("Failure to reclaim VWAP weakens directional quality.")

        if 50 <= rsi_5m <= 68:
            expansion_quality += 10
        elif rsi_5m >= 74:
            expansion_quality -= 10
            warnings.append("Momentum extension increases exhaustion probability.")

        if "high-quality" in execution_quality:
            expansion_quality += 8
        elif "poor" in execution_quality:
            expansion_quality -= 12

        if "trend" in personality.lower():
            sponsorship_score += 6
        elif "rotation" in personality.lower() or "chop" in personality.lower():
            expansion_quality -= 8

        if "high" in trap_risk or "elevated" in trap_risk:
            expansion_quality -= 14
            warnings.append("Liquidity trap behavior detected inside expansion conditions.")

        sponsorship_score = self._clamp(sponsorship_score)
        liquidity_pressure = self._clamp(liquidity_pressure)
        expansion_quality = self._clamp(expansion_quality)

        expansion_state = self._expansion_state(expansion_quality, sponsorship_score)

        notes.append(f"Institutional flow regime: {expansion_state}.")

        return {
            "expansion_state": expansion_state,
            "institutional_sponsorship_score": sponsorship_score,
            "liquidity_pressure_score": liquidity_pressure,
            "expansion_quality_score": expansion_quality,
            "flow_alignment": expansion_quality >= 62 and sponsorship_score >= 60,
            "momentum_sponsorship": sponsorship_score >= 65,
            "expansion_confirmations": confirmations[:6],
            "warnings": warnings[:6] or ["No abnormal institutional flow instability detected."],
            "notes": notes[:5],
        }

    def _expansion_state(self, expansion_quality: int, sponsorship_score: int) -> str:
        if expansion_quality >= 75 and sponsorship_score >= 70:
            return "institutional expansion acceleration"
        if expansion_quality >= 62:
            return "constructive directional expansion"
        if expansion_quality <= 35:
            return "suppressed expansion environment"
        return "mixed institutional participation"

    def _clamp(self, value: int) -> int:
        return max(5, min(95, int(value)))
