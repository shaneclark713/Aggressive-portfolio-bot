from typing import Any


def build_spy_report(payload: dict[str, Any], title: str) -> str:
    structure = payload.get('structure', {})
    dealer = payload.get('dealer_gamma', {})
    probs = payload.get('probabilities', {})
    ecosystem = payload.get('ecosystem', {})
    trap = payload.get('trap_detection', {})

    return '\n'.join([
        f'<b>{title}</b>',
        '',
        f"SPY: {payload.get('latest',0)} | VWAP: {payload.get('vwap',0)}",
        f"Structure: {structure.get('bias','n/a')} ({structure.get('score',0)})",
        f"Dealer: {dealer.get('dealer_regime','n/a')}",
        f"Trend Prob: {probs.get('trend_probability',0)}%",
        f"Trap Risk: {trap.get('risk_state','normal')}",
        f"Ecosystem: {ecosystem.get('ecosystem_label','n/a')}",
    ])