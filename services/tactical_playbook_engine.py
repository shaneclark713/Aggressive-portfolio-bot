from __future__ import annotations

from typing import Any


class TacticalPlaybookEngine:
    """Institutional tactical playbook selector.

    Determines which execution framework best matches the current
    market structure.
    """

    def select(
        self,
        structure: dict[str, Any],
        dealer_gamma: dict[str, Any],
        cross_market: dict[str, Any],
        narrative: dict[str, Any],
        rsi_5m: float,
        latest: float,
        vwap: float,
    ) -> dict[str, Any]:
        bias = str(structure.get("bias", "balanced / tactical"))
        dealer = str(dealer_gamma.get("dealer_regime", "balanced dealer pressure"))
        tone = str(cross_market.get("tone", "mixed / neutral"))
        environment = str(narrative.get("environment", "balanced tactical environment"))

        if "upside" in bias and "risk-on" in tone and latest > vwap:
            return self._trend_continuation(rsi_5m)

        if "downside" in bias and latest < vwap:
            return self._failed_breakout_fade(rsi_5m)

        if "pin risk" in dealer:
            return self._gamma_pin_chop()

        if "balanced" in bias:
            return self._rotational_environment()

        return self._default(environment)

    def _trend_continuation(self, rsi_5m: float) -> dict[str, Any]:
        return {
            "playbook": "ORB Trend Continuation",
            "environment": "momentum expansion",
            "preferred_entries": [
                "ORB reclaim",
                "VWAP hold",
                "higher low continuation",
            ],
            "avoid": [
                "late breakout chasing",
                "entries during vertical extension",
            ],
            "runner_allowed": rsi_5m < 72,
            "risk_profile": "moderate-aggressive",
            "notes": [
                "Momentum conditions support continuation trades.",
                "Allow partial runners only after confirmation stacking.",
            ],
        }

    def _failed_breakout_fade(self, rsi_5m: float) -> dict[str, Any]:
        return {
            "playbook": "Failed Breakout Fade",
            "environment": "reversal / liquidity flush",
            "preferred_entries": [
                "VWAP rejection",
                "failed ORB reclaim",
                "lower-high rejection",
            ],
            "avoid": [
                "blind dip buying",
                "counter-trend calls",
            ],
            "runner_allowed": rsi_5m > 30,
            "risk_profile": "defensive",
            "notes": [
                "Breakout structure weakening.",
                "Watch for liquidity sweeps and failed reclaim attempts.",
            ],
        }

    def _gamma_pin_chop(self) -> dict[str, Any]:
        return {
            "playbook": "Gamma Pin Rotation",
            "environment": "dealer-controlled chop",
            "preferred_entries": [
                "mean reversion",
                "range edge scalps",
            ],
            "avoid": [
                "holding runners",
                "overstaying trend attempts",
            ],
            "runner_allowed": False,
            "risk_profile": "conservative",
            "notes": [
                "Dealer positioning favors rotational behavior.",
                "Take profits faster and reduce overtrading.",
            ],
        }

    def _rotational_environment(self) -> dict[str, Any]:
        return {
            "playbook": "Balanced Tactical Rotation",
            "environment": "mixed auction",
            "preferred_entries": [
                "confirmation-based scalps",
                "VWAP reactions",
            ],
            "avoid": [
                "predictive entries",
                "large position sizing",
            ],
            "runner_allowed": False,
            "risk_profile": "balanced",
            "notes": [
                "Market lacks strong directional commitment.",
                "Wait for confirmation instead of anticipating expansion.",
            ],
        }

    def _default(self, environment: str) -> dict[str, Any]:
        return {
            "playbook": "Adaptive Tactical",
            "environment": environment,
            "preferred_entries": ["confirmation only"],
            "avoid": ["forcing trades"],
            "runner_allowed": False,
            "risk_profile": "balanced",
            "notes": [
                "No dominant tactical environment detected.",
            ],
        }
