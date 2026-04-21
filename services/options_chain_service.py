from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable


@dataclass(slots=True)
class OptionContract:
    option_symbol: str
    underlying: str
    option_type: str
    strike: float
    expiry: str
    delta: float
    implied_volatility: float
    open_interest: int
    volume: int
    bid: float
    ask: float
    mark: float
    expiry_type: str = "any"

    def to_dict(self) -> dict[str, Any]:
        return {
            "option_symbol": self.option_symbol,
            "underlying": self.underlying,
            "option_type": self.option_type,
            "strike": self.strike,
            "expiry": self.expiry,
            "delta": self.delta,
            "implied_volatility": self.implied_volatility,
            "open_interest": self.open_interest,
            "volume": self.volume,
            "bid": self.bid,
            "ask": self.ask,
            "mark": self.mark,
            "expiry_type": self.expiry_type,
        }


class OptionsChainService:
    def normalize_contracts(self, underlying: str, rows: Iterable[dict]) -> list[dict]:
        normalized: list[dict] = []
        for row in rows or []:
            try:
                bid = float(row.get("bid", 0) or 0)
                ask = float(row.get("ask", 0) or 0)
                mark = float(row.get("mark", 0) or 0)
                if mark <= 0:
                    mark = round((bid + ask) / 2, 4) if bid > 0 and ask > 0 else max(bid, ask, 0.0)
                contract = OptionContract(
                    option_symbol=str(row.get("option_symbol") or row.get("symbol") or ""),
                    underlying=str(row.get("underlying") or underlying),
                    option_type=str(row.get("option_type") or row.get("type") or "call").lower(),
                    strike=float(row.get("strike", 0) or 0),
                    expiry=str(row.get("expiry") or row.get("expiration_date") or ""),
                    delta=float(row.get("delta", 0) or 0),
                    implied_volatility=float(row.get("implied_volatility", row.get("iv", 0)) or 0),
                    open_interest=int(row.get("open_interest", 0) or 0),
                    volume=int(row.get("volume", 0) or 0),
                    bid=bid,
                    ask=ask,
                    mark=mark,
                    expiry_type=str(row.get("expiry_type") or "any").lower(),
                )
            except Exception:
                continue

            if not contract.option_symbol or contract.strike <= 0:
                continue
            normalized.append(contract.to_dict())
        return normalized

    def summarize_chain(self, rows: Iterable[dict]) -> dict[str, Any]:
        contracts = list(rows or [])
        calls = sum(1 for r in contracts if str(r.get("option_type", "")).lower() == "call")
        puts = sum(1 for r in contracts if str(r.get("option_type", "")).lower() == "put")
        total_oi = sum(int(r.get("open_interest", 0) or 0) for r in contracts)
        total_volume = sum(int(r.get("volume", 0) or 0) for r in contracts)
        avg_mark = round(
            sum(float(r.get("mark", 0) or 0) for r in contracts) / len(contracts),
            4,
        ) if contracts else 0.0
        return {
            "contract_count": len(contracts),
            "call_count": calls,
            "put_count": puts,
            "total_open_interest": total_oi,
            "total_volume": total_volume,
            "avg_mark": avg_mark,
        }
