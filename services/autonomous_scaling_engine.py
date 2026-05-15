from __future__ import annotations

from typing import Any


class AutonomousScalingEngine:
    """Autonomous trade scaling and profit-management engine.

    Produces structured guidance for partial exits, runner handling,
    breakeven movement, and de-risking. This engine does not place orders by
    itself; execution routers must still enforce mode, broker, and risk gates.
    """

    def plan(
        self,
        probabilities: dict[str, Any],
        playbook: dict[str, Any],
        adaptive_exits: dict[str, Any],
        execution_timing: dict[str, Any],
        rsi_5m: float,
    ) -> dict[str, Any]:
        runner_probability = int(probabilities.get("runner_probability") or 0)
        trap_probability = int(probabilities.get("trap_probability") or 0)
        expansion_probability = int(probabilities.get("gamma_expansion_probability") or 0)
        trend_probability = int(probabilities.get("trend_probability") or 0)

        runner_allowed = bool(adaptive_exits.get("runner_allowed"))
        hold_strength = int(adaptive_exits.get("hold_strength") or 0)
        playbook_name = str(playbook.get("playbook") or "Adaptive Tactical")
        timing_quality = str(execution_timing.get("execution_quality") or "mixed")

        partial_1 = 0.18
        partial_2 = 0.32
        runner_size = 0.20
        stop_policy = "move_to_breakeven_after_partial_1"
        scale_mode = "standard_scale_out"
        de_risk = False

        notes: list[str] = []
        safeguards: list[str] = []

        if trend_probability >= 65 and expansion_probability >= 55:
            partial_1 = 0.22
            partial_2 = 0.42
            runner_size = 0.30
            scale_mode = "trend_expansion_scale_out"
            notes.append("Trend and gamma expansion probabilities support wider profit targets.")

        if runner_allowed and runner_probability >= 55 and hold_strength >= 60:
            runner_size = max(runner_size, 0.30)
            stop_policy = "breakeven_then_adaptive_trail"
            notes.append("Runner quality supports keeping a larger final portion after partials.")
        else:
            runner_size = min(runner_size, 0.15)
            safeguards.append("Runner quality is not strong enough for extended hold behavior.")

        if trap_probability >= 55:
            partial_1 = 0.12
            partial_2 = 0.24
            runner_size = 0.0
            stop_policy = "tight_stop_after_first_profit"
            scale_mode = "defensive_fast_scale_out"
            de_risk = True
            safeguards.append("Trap risk elevated; scale faster and avoid runner exposure.")

        if "Gamma Pin" in playbook_name:
            partial_1 = 0.10
            partial_2 = 0.18
            runner_size = 0.0
            scale_mode = "pin_environment_quick_scalp"
            de_risk = True
            safeguards.append("Gamma pin conditions favor quick profits and no runners.")

        if "poor" in timing_quality:
            partial_1 = min(partial_1, 0.12)
            runner_size = 0.0
            de_risk = True
            safeguards.append("Poor execution timing requires reduced hold duration.")

        if rsi_5m >= 75:
            runner_size = min(runner_size, 0.10)
            stop_policy = "aggressive_profit_lock"
            safeguards.append("RSI extension increases reversal risk; lock gains faster.")

        if not notes:
            notes.append("Standard scaling applies until stronger continuation evidence appears.")

        return {
            "scale_mode": scale_mode,
            "partial_1_target_pct": round(partial_1 * 100, 1),
            "partial_2_target_pct": round(partial_2 * 100, 1),
            "runner_size_pct": round(runner_size * 100, 1),
            "stop_policy": stop_policy,
            "de_risk_required": de_risk,
            "notes": notes[:5],
            "safeguards": safeguards[:6] or ["No abnormal scaling safeguard triggered."],
        }
