from __future__ import annotations

from typing import Any, Dict, Iterable


class IVAnalyzer:
    def summarize_chain(self, contracts: Iterable[dict]) -> Dict[str, Any]:
        rows = list(contracts or [])
        ivs = []
        oi = 0
        volume = 0

        for contract in rows:
            iv = contract.get("implied_volatility")
            if iv is not None:
                try:
                    ivs.append(float(iv))
                except Exception:
                    pass
            oi += int(contract.get("open_interest", 0) or 0)
            volume += int(contract.get("volume", 0) or 0)

        avg_iv = round(sum(ivs) / len(ivs), 4) if ivs else 0.0
        regime = "elevated" if avg_iv >= 0.60 else "moderate" if avg_iv >= 0.30 else "low"

        return {
            "contract_count": len(rows),
            "avg_iv": avg_iv,
            "total_open_interest": oi,
            "total_volume": volume,
            "iv_regime": regime,
        }
