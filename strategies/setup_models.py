from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass(slots=True)
class SetupResult:
    symbol: str
    signal: str
    strategy: str
    confidence: int = 0
    trigger_reasons: List[str] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "signal": self.signal,
            "strategy": self.strategy,
            "confidence": self.confidence,
            "trigger_reasons": list(self.trigger_reasons),
            "metrics": dict(self.metrics),
            "metadata": dict(self.metadata),
        }
