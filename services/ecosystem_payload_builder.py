from typing import Any


def build_ecosystem_payload(*, trade_memory: dict[str, Any], ai_review: dict[str, Any], institutional_flow: dict[str, Any], theta_protection: dict[str, Any], autonomous_mutation: dict[str, Any], session_personality: dict[str, Any], probabilities: dict[str, Any], cross_market: dict[str, Any], trap_detection: dict[str, Any], dealer_gamma: dict[str, Any], events: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        'trade_memory': trade_memory,
        'ai_review': ai_review,
        'institutional_flow': institutional_flow,
        'theta_protection': theta_protection,
        'autonomous_mutation': autonomous_mutation,
        'session_personality': session_personality,
        'probabilities': probabilities,
        'cross_market': cross_market,
        'trap_detection': trap_detection,
        'dealer_gamma': dealer_gamma,
        'events': events,
    }
