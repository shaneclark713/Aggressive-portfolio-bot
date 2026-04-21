from __future__ import annotations

from typing import Any, Dict, Iterable


class OptionsStrategy:
    def select_best_contract(self, contracts: Iterable[dict]) -> Dict[str, Any] | None:
        rows = list(contracts or [])
        if not rows:
            return None

        ranked = sorted(
            rows,
            key=lambda x: (
                float(x.get("open_interest", 0) or 0),
                float(x.get("volume", 0) or 0),
                -abs(abs(float(x.get("delta", 0.5) or 0.5)) - 0.50),
            ),
            reverse=True,
        )
        return ranked[0]
