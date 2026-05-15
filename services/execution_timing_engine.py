from __future__ import annotations

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo


class ExecutionTimingEngine:
    """Institutional execution timing intelligence.

    Evaluates intraday conditions to determine when execution quality is
    strongest or weakest.
    """

    def __init__(self):
        self.market_tz = ZoneInfo("America/New_York")

    def analyze(
        self,
        structure: dict[str, Any],
        probabilities: dict[str, Any],
        latest: float,
        vwap: float,
    ) -> dict[str, Any]:
        now = datetime.now(self.market_tz)
        minutes = now.hour * 60 + now.minute

        trend_probability = int(probabilities.get("trend_probability") or 0)
        trap_probability = int(probabilities.get("trap_probability") or 0)
        mean_reversion = int(probabilities.get("mean_reversion_probability") or 0)

        opening_drive = self._opening_drive(minutes, structure)
        session_state = self._session_state(minutes)
        timing_score = self._timing_score(minutes, trend_probability, trap_probability)

        conditions: list[str] = []
        risks: list[str] = []
        opportunities: list[str] = []

        if session_state == "opening_expansion_window":
            opportunities.append("Opening-drive volatility can produce strong directional moves.")
            conditions.append("Require confirmation before entering during early volatility.")

        if session_state == "midday_decay_window":
            risks.append("Midday premium decay and rotational chop risk elevated.")
            conditions.append("Favor faster scalps and reduced runner exposure.")

        if session_state == "power_hour_window":
            opportunities.append("Institutional repositioning can fuel late-day expansion.")
            conditions.append("Watch for breakout continuation after afternoon compression.")

        if trend_probability >= 65:
            opportunities.append("Trend conditions support continuation after confirmation stacking.")

        if trap_probability >= 55:
            risks.append("Liquidity sweep risk elevated; avoid chasing extension.")

        if mean_reversion >= 60:
            risks.append("Dealer-controlled rotational behavior likely inside range.")

        if latest > vwap:
            conditions.append("Buy-side control remains stronger while above VWAP.")
        elif latest < vwap:
            conditions.append("Sell-side control remains stronger while below VWAP.")

        if not opportunities:
            opportunities.append("No dominant timing edge currently detected.")

        if not risks:
            risks.append("No abnormal intraday timing risk detected.")

        return {
            "session_state": session_state,
            "opening_drive": opening_drive,
            "timing_score": timing_score,
            "execution_quality": self._quality_label(timing_score),
            "conditions": conditions[:6],
            "opportunities": opportunities[:5],
            "risks": risks[:5],
        }

    def _opening_drive(self, minutes: int, structure: dict[str, Any]) -> str:
        bias = str(structure.get("bias") or "balanced")

        if minutes < 630:
            return "premarket positioning"

        if 570 <= minutes <= 615:
            if "upside" in bias:
                return "bullish opening drive"
            if "downside" in bias:
                return "bearish opening drive"
            return "balanced opening auction"

        return "post-opening structure"

    def _session_state(self, minutes: int) -> str:
        if 570 <= minutes <= 630:
            return "opening_expansion_window"

        if 690 <= minutes <= 810:
            return "midday_decay_window"

        if 900 <= minutes <= 960:
            return "power_hour_window"

        return "normal_session_conditions"

    def _timing_score(self, minutes: int, trend_probability: int, trap_probability: int) -> int:
        score = 50

        if 570 <= minutes <= 630:
            score += 12

        if 900 <= minutes <= 960:
            score += 10

        if 690 <= minutes <= 810:
            score -= 15

        score += int((trend_probability - 50) * 0.35)
        score -= int((trap_probability - 50) * 0.25)

        return max(5, min(95, score))

    def _quality_label(self, score: int) -> str:
        if score >= 75:
            return "high-quality execution window"

        if score >= 60:
            return "constructive execution conditions"

        if score <= 35:
            return "poor execution conditions"

        return "mixed execution conditions"
