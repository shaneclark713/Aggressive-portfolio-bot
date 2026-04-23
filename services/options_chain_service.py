from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from math import ceil
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
    last: float
    mark: float
    expiry_type: str = "any"
    days_to_expiry: int | None = None
    weeks_to_expiry: int | None = None
    months_to_expiry: int | None = None

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
            "last": self.last,
            "mark": self.mark,
            "expiry_type": self.expiry_type,
            "days_to_expiry": self.days_to_expiry,
            "weeks_to_expiry": self.weeks_to_expiry,
            "months_to_expiry": self.months_to_expiry,
        }


class OptionsChainService:
    @staticmethod
    def _to_float(value: Any, default: float = 0.0) -> float:
        try:
            if value is None or value == "":
                return default
            return float(value)
        except Exception:
            return default

    @staticmethod
    def _to_int(value: Any, default: int = 0) -> int:
        try:
            if value is None or value == "":
                return default
            return int(float(value))
        except Exception:
            return default

    @staticmethod
    def _parse_expiry(raw: Any) -> date | None:
        if not raw:
            return None
        text = str(raw).strip()
        for fmt in ("%Y-%m-%d", "%Y%m%d", "%m/%d/%Y"):
            try:
                return datetime.strptime(text, fmt).date()
            except Exception:
                continue
        try:
            return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
        except Exception:
            return None

    def _derive_expiry_fields(self, expiry_raw: Any) -> tuple[int | None, int | None, int | None, str]:
        expiry_date = self._parse_expiry(expiry_raw)
        if expiry_date is None:
            return None, None, None, "any"
        today = datetime.now(timezone.utc).date()
        dte = max((expiry_date - today).days, 0)
        weeks = 0 if dte == 0 else ceil(dte / 7)
        months = 0 if dte == 0 else ceil(dte / 30)
        if dte == 0:
            expiry_type = "0dte"
        elif dte <= 21:
            expiry_type = "weekly"
        else:
            expiry_type = "monthly"
        return dte, weeks, months, expiry_type

    def normalize_contracts(self, underlying: str, rows: Iterable[dict]) -> list[dict]:
        normalized: list[dict] = []
        for row in rows or []:
            try:
                bid = self._to_float(row.get("bid"))
                ask = self._to_float(row.get("ask"))
                last = self._to_float(row.get("last", row.get("last_price", 0)))
                mark = self._to_float(row.get("mark"))
                if mark <= 0:
                    if bid > 0 and ask > 0:
                        mark = round((bid + ask) / 2, 4)
                    else:
                        mark = max(last, bid, ask, 0.0)
                dte, weeks, months, expiry_type = self._derive_expiry_fields(row.get("expiry") or row.get("expiration_date"))
                contract = OptionContract(
                    option_symbol=str(row.get("option_symbol") or row.get("symbol") or ""),
                    underlying=str(row.get("underlying") or underlying),
                    option_type=str(row.get("option_type") or row.get("type") or "call").lower(),
                    strike=self._to_float(row.get("strike")),
                    expiry=str(row.get("expiry") or row.get("expiration_date") or ""),
                    delta=self._to_float(row.get("delta")),
                    implied_volatility=self._to_float(row.get("implied_volatility", row.get("iv", 0))),
                    open_interest=self._to_int(row.get("open_interest", row.get("openInterest", 0))),
                    volume=self._to_int(row.get("volume")),
                    bid=bid,
                    ask=ask,
                    last=last,
                    mark=mark,
                    expiry_type=str(row.get("expiry_type") or expiry_type).lower(),
                    days_to_expiry=dte,
                    weeks_to_expiry=weeks,
                    months_to_expiry=months,
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
        total_oi = sum(self._to_int(r.get("open_interest", 0)) for r in contracts)
        total_volume = sum(self._to_int(r.get("volume", 0)) for r in contracts)
        avg_mark = round(sum(self._to_float(r.get("mark", 0)) for r in contracts) / len(contracts), 4) if contracts else 0.0
        zero_dte = sum(1 for r in contracts if self._to_int(r.get("days_to_expiry", 0)) == 0)
        return {
            "contract_count": len(contracts),
            "call_count": calls,
            "put_count": puts,
            "total_open_interest": total_oi,
            "total_volume": total_volume,
            "avg_mark": avg_mark,
            "zero_dte_count": zero_dte,
        }
