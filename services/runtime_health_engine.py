from __future__ import annotations

from typing import Any

class RuntimeHealthEngine:
    """Runtime health scoring for deployment readiness."""

    def evaluate(self, payload: dict[str, Any]) -> dict[str, Any]:
        api_health = int(payload.get('api_health_score', 100) or 100)
        market_confidence = int(payload.get('market_data_confidence', 100) or 100)
        execution_confidence = int(payload.get('execution_confidence', 100) or 100)
        missing_feeds = int(payload.get('missing_feeds', 0) or 0)
        timeout_count = int(payload.get('timeout_count', 0) or 0)

        runtime_score = int(api_health*0.3 + market_confidence*0.25 + execution_confidence*0.25 + max(0,100-missing_feeds*15)*0.1 + max(0,100-timeout_count*10)*0.1)
        runtime_score = max(0,min(100,runtime_score))

        mode='normal'
        if runtime_score <= 40:
            mode='failsafe'
        elif runtime_score <= 60:
            mode='degraded'
        elif runtime_score <= 75:
            mode='cautious'

        return {'runtime_score':runtime_score,'runtime_mode':mode,'allow_autonomy':runtime_score>=65}
