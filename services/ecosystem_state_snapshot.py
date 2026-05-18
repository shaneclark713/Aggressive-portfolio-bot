from typing import Any


def build_ecosystem_state(*, ecosystem: dict[str, Any], risk_regime: dict[str, Any] | None = None, runtime_health: dict[str, Any] | None = None, feedback: dict[str, Any] | None = None, deployment_mode: str = 'paper', state_persistence: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        'ecosystem': ecosystem,
        'risk_regime': risk_regime or {},
        'runtime_health': runtime_health or {},
        'feedback': feedback or {},
        'deployment_mode': deployment_mode,
        'state_persistence': state_persistence or {},
    }
