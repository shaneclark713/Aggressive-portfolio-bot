from __future__ import annotations

from typing import Any


class ProbabilityMatrixEngine:
    """Institutional probability matrix for SPY/XSP tactical scans.

    Converts structure, dealer positioning, cross-market tone, RSI, and playbook
    context into scenario probabilities used by reporting and autonomy.
    """

    def build(
        self,
        structure: dict[str, Any],
        dealer_gamma: dict[str, Any],
        cross_market: dict[str, Any],
        narrative: dict[str, Any],
        playbook: dict[str, Any],
        rsi_5m: float,
        latest: float,
        vwap: float,
    ) -> dict[str, Any]:
        structure_score = int(structure.get("score") or 0)
        dealer_regime = str(dealer_gamma.get("dealer_regime") or "unknown")
        cross_tone = str(cross_market.get("tone") or "mixed / neutral")
        playbook_name = str(playbook.get("playbook") or "Adaptive Tactical")

        trend = 45
        mean_reversion = 45
        reversal = 25
        trap = 25
        expansion = 30
        runner = 20

        if structure_score >= 35:
            trend += 18
            expansion += 12
            runner += 10
            mean_reversion -= 10
        elif structure_score <= -35:
            trend += 10
            reversal += 15
            expansion += 8
            mean_reversion -= 5
        elif abs(structure_score) < 20:
            mean_reversion += 15
            trap += 10
            trend -= 8

        if "risk-on" in cross_tone or "supportive" in cross_tone:
            trend += 10
            runner += 8
            trap -= 5
        elif "risk-off" in cross_tone or "defensive" in cross_tone:
            reversal += 10
            trap += 8
            runner -= 5

        if "pin risk" in dealer_regime:
            mean_reversion += 18
            trap += 12
            trend -= 10
            runner -= 15
        elif "call-heavy" in dealer_regime or "chase pressure" in dealer_regime:
            trend += 12
            expansion += 15
            runner += 12
        elif "put-heavy" in dealer_regime or "hedge pressure" in dealer_regime:
            reversal += 12
            expansion += 12
            trap += 5

        if latest > vwap:
            trend += 8
            runner += 5
        elif latest < vwap:
            reversal += 8
            mean_reversion += 4

        if rsi_5m >= 72:
            trap += 15
            reversal += 10
            runner -= 10
        elif rsi_5m <= 32:
            mean_reversion += 12
            reversal -= 5
        elif 50 <= rsi_5m <= 68:
            trend += 8
            runner += 6

        if "Trend Continuation" in playbook_name:
            trend += 10
            runner += 10
            expansion += 8
        elif "Failed Breakout" in playbook_name:
            reversal += 12
            trap += 8
        elif "Gamma Pin" in playbook_name:
            mean_reversion += 15
            runner -= 12
        elif "Rotation" in playbook_name:
            mean_reversion += 10
            trap += 5

        trend = self._clamp(trend)
        mean_reversion = self._clamp(mean_reversion)
        reversal = self._clamp(reversal)
        trap = self._clamp(trap)
        expansion = self._clamp(expansion)
        runner = self._clamp(runner)

        primary = self._primary_scenario(
            trend=trend,
            mean_reversion=mean_reversion,
            reversal=reversal,
            trap=trap,
            expansion=expansion,
        )

        return {
            "primary_scenario": primary,
            "trend_probability": trend,
            "mean_reversion_probability": mean_reversion,
            "reversal_probability": reversal,
            "trap_probability": trap,
            "gamma_expansion_probability": expansion,
            "runner_probability": runner,
            "notes": self._notes(primary, trend, mean_reversion, reversal, trap, expansion, runner),
        }

    def _clamp(self, value: int) -> int:
        return max(5, min(95, int(value)))

    def _primary_scenario(self, **values: int) -> str:
        ordered = sorted(values.items(), key=lambda item: item[1], reverse=True)
        key = ordered[0][0]
        return {
            "trend": "trend continuation",
            "mean_reversion": "mean-reversion / range control",
            "reversal": "reversal / failed move",
            "trap": "trap / liquidity sweep risk",
            "expansion": "gamma expansion",
        }.get(key, key)

    def _notes(
        self,
        primary: str,
        trend: int,
        mean_reversion: int,
        reversal: int,
        trap: int,
        expansion: int,
        runner: int,
    ) -> list[str]:
        notes = [f"Primary scenario is {primary}."]
        if trend >= 65:
            notes.append("Trend probability is high enough to respect continuation after confirmation.")
        if mean_reversion >= 60:
            notes.append("Mean-reversion probability is elevated; avoid chasing range extremes.")
        if reversal >= 55:
            notes.append("Reversal probability is meaningful; watch VWAP and ORB failures.")
        if trap >= 55:
            notes.append("Trap risk is elevated; require confirmation before entry.")
        if expansion >= 60:
            notes.append("Gamma expansion risk is elevated; premium can move quickly after breakouts.")
        if runner >= 55:
            notes.append("Runner conditions may be valid after partial profits and confirmation hold.")
        elif runner <= 25:
            notes.append("Runner quality is weak; faster profit-taking is favored.")
        return notes[:6]
