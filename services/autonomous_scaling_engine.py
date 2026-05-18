from __future__ import annotations

from typing import Any


class AutonomousScalingEngine:
    """Autonomous trade scaling and adaptive governance engine."""

    def plan(self, probabilities: dict[str, Any], playbook: dict[str, Any], adaptive_exits: dict[str, Any], execution_timing: dict[str, Any], rsi_5m: float,) -> dict[str, Any]:
        runner_probability=int(probabilities.get('runner_probability') or 0)
        trap_probability=int(probabilities.get('trap_probability') or 0)
        expansion_probability=int(probabilities.get('gamma_expansion_probability') or 0)
        trend_probability=int(probabilities.get('trend_probability') or 0)

        runner_allowed=bool(adaptive_exits.get('runner_allowed'))
        hold_strength=int(adaptive_exits.get('hold_strength') or 0)
        playbook_name=str(playbook.get('playbook') or 'Adaptive Tactical')
        timing_quality=str(execution_timing.get('execution_quality') or 'mixed')

        partial_1=0.18; partial_2=0.32; runner_size=0.20
        stop_policy='move_to_breakeven_after_partial_1'
        scale_mode='standard_scale_out'; de_risk=False
        max_contracts=3
        governance='balanced'

        notes=[]; safeguards=[]

        if trend_probability>=65 and expansion_probability>=55:
            partial_1=0.22; partial_2=0.42; runner_size=0.30
            scale_mode='trend_expansion_scale_out'; max_contracts=5
            notes.append('Trend expansion supports wider targets and increased size.')

        if trap_probability>=55:
            partial_1=0.12; partial_2=0.24; runner_size=0.0
            scale_mode='defensive_fast_scale_out'; de_risk=True
            max_contracts=1; governance='defensive'
            safeguards.append('Trap risk elevated; restricting position size.')

        if 'Gamma Pin' in playbook_name:
            partial_1=0.10; partial_2=0.18; runner_size=0.0
            max_contracts=1; governance='pin_controlled'

        if 'poor' in timing_quality:
            max_contracts=min(max_contracts,1)
            governance='timing_restricted'

        if rsi_5m>=75:
            runner_size=min(runner_size,0.10)
            stop_policy='aggressive_profit_lock'

        drawdown_governor='normal'
        if hold_strength<45:
            drawdown_governor='reduced_exposure'
            max_contracts=min(max_contracts,2)

        return {'scale_mode':scale_mode,'partial_1_target_pct':round(partial_1*100,1),'partial_2_target_pct':round(partial_2*100,1),'runner_size_pct':round(runner_size*100,1),'stop_policy':stop_policy,'de_risk_required':de_risk,'max_contracts':max_contracts,'governance_mode':governance,'drawdown_governor':drawdown_governor,'notes':notes[:5],'safeguards':safeguards[:6] or ['No abnormal scaling safeguard triggered.']}
