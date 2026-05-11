from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class DealerGammaSummary:
    pin: str
    flip: str
    support: str
    resistance: str
    dealer_regime: str
    exposure_score: int
    notes: list[str]

    def as_dict(self) -> dict[str, Any]:
        return {
            "pin": self.pin,
            "flip": self.flip,
            "support": self.support,
            "resistance": self.resistance,
            "dealer_regime": self.dealer_regime,
            "exposure_score": self.exposure_score,
            "notes": self.notes,
        }


class DealerGammaService:
    """Lightweight option-chain concentration and dealer-regime estimator.

    This is not a true broker/dealer GEX feed. It derives a practical intraday
    estimate from same-expiration option-chain strike concentration using open
    interest, volume, and available greeks. The output is meant for report
    context and gating, not automatic order submission.
    """

    def _safe_float(self, value: Any, default: float = 0.0) -> float:
        try:
            if value is None:
                return default
            return float(value)
        except Exception:
            return default

    def _row_delta(self, row: dict[str, Any]) -> float:
        greeks = row.get("greeks") if isinstance(row.get("greeks"), dict) else {}
        return self._safe_float(row.get("delta") or greeks.get("delta"), 0.0)

    def _row_gamma(self, row: dict[str, Any]) -> float:
        greeks = row.get("greeks") if isinstance(row.get("greeks"), dict) else {}
        return abs(self._safe_float(row.get("gamma") or greeks.get("gamma"), 0.0))

    def _row_option_type(self, row: dict[str, Any]) -> str:
        raw = str(row.get("option_type") or row.get("type") or row.get("put_call") or "").lower()
        if raw.startswith("p"):
            return "put"
        if raw.startswith("c"):
            return "call"
        symbol = str(row.get("symbol") or row.get("option_symbol") or "").upper()
        # OCC symbols usually contain C/P before strike digits near the end.
        if len(symbol) > 15:
            tail = symbol[-9:]
            marker = symbol[-9:-8]
            if marker == "P":
                return "put"
            if marker == "C":
                return "call"
        return "unknown"

    def _row_weight(self, row: dict[str, Any]) -> float:
        open_interest = self._safe_float(row.get("open_interest") or row.get("openInterest"), 0.0)
        volume = self._safe_float(row.get("volume"), 0.0)
        gamma = self._row_gamma(row)
        # Volume matters intraday but should not swamp open interest entirely.
        base = open_interest + (volume * 0.35)
        return base * (1.0 + min(gamma * 100.0, 2.0))

    def summarize(self, latest: float, chain_rows: list[dict[str, Any]]) -> DealerGammaSummary:
        if not latest or not chain_rows:
            return DealerGammaSummary(
                pin="n/a",
                flip="n/a",
                support="n/a",
                resistance="n/a",
                dealer_regime="unknown",
                exposure_score=0,
                notes=["Option-chain data unavailable; dealer regime cannot be estimated."],
            )

        strike_weights: dict[float, float] = {}
        call_weight = 0.0
        put_weight = 0.0
        near_money_weight = 0.0

        for row in chain_rows:
            strike = self._safe_float(row.get("strike"), 0.0)
            if not strike:
                continue
            weight = self._row_weight(row)
            if weight <= 0:
                continue
            strike_weights[strike] = strike_weights.get(strike, 0.0) + weight
            option_type = self._row_option_type(row)
            if option_type == "call":
                call_weight += weight
            elif option_type == "put":
                put_weight += weight
            if abs(strike - latest) / latest <= 0.01:
                near_money_weight += weight

        if not strike_weights:
            return DealerGammaSummary(
                pin="n/a",
                flip="n/a",
                support="n/a",
                resistance="n/a",
                dealer_regime="unknown",
                exposure_score=0,
                notes=["No usable strike concentration found in option chain."],
            )

        ranked = sorted(strike_weights.items(), key=lambda item: item[1], reverse=True)
        pin = ranked[0][0]
        above = [strike for strike, _ in ranked if strike > latest]
        below = [strike for strike, _ in ranked if strike < latest]
        resistance = min(above, key=lambda value: abs(value - latest)) if above else pin
        support = min(below, key=lambda value: abs(value - latest)) if below else pin
        flip = (support + resistance) / 2 if support and resistance else pin

        total_weight = max(call_weight + put_weight, 1.0)
        put_call_pressure = (put_weight - call_weight) / total_weight
        near_money_ratio = near_money_weight / max(sum(strike_weights.values()), 1.0)

        exposure_score = int(max(-100, min(100, round((near_money_ratio * 100.0) - (abs(put_call_pressure) * 25.0)))))
        notes: list[str] = []

        if near_money_ratio >= 0.35:
            dealer_regime = "pin risk / long-gamma style behavior"
            notes.append("Large near-the-money concentration can suppress realized movement and favor mean reversion.")
        elif put_call_pressure > 0.25:
            dealer_regime = "put-heavy hedge pressure"
            notes.append("Put-side concentration is elevated; downside moves can accelerate if support breaks.")
        elif put_call_pressure < -0.25:
            dealer_regime = "call-heavy chase pressure"
            notes.append("Call-side concentration is elevated; upside can squeeze but failed breakouts may reverse quickly.")
        else:
            dealer_regime = "balanced dealer pressure"
            notes.append("Call/put concentration is balanced; price structure should lead the read.")

        if latest > resistance:
            notes.append("Price is above nearby weighted resistance; watch for continuation versus failed-break reversal.")
        elif latest < support:
            notes.append("Price is below nearby weighted support; watch for acceleration versus reflex reclaim.")
        else:
            notes.append("Price is trading between nearby weighted support and resistance.")

        return DealerGammaSummary(
            pin=f"{pin:.2f}",
            flip=f"{flip:.2f}",
            support=f"{support:.2f}",
            resistance=f"{resistance:.2f}",
            dealer_regime=dealer_regime,
            exposure_score=exposure_score,
            notes=notes[:4],
        )
