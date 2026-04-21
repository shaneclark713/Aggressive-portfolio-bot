from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from services.options_chain_service import OptionsChainService


class OptionsChainIngestService:
    CHAIN_KEY = "__meta__.ui.last_option_chain"
    FLOW_KEY = "__meta__.ui.options_flow_rows"

    def __init__(self, settings_repo, tradier_client, chain_service: OptionsChainService | None = None):
        self.settings_repo = settings_repo
        self.tradier_client = tradier_client
        self.chain_service = chain_service or OptionsChainService()

    def _extract_delta(self, row: dict[str, Any]) -> float:
        greeks = row.get("greeks") or {}
        for key in ("delta",):
            if row.get(key) is not None:
                return float(row.get(key) or 0)
            if greeks.get(key) is not None:
                return float(greeks.get(key) or 0)
        return 0.0

    def _extract_iv(self, row: dict[str, Any]) -> float:
        greeks = row.get("greeks") or {}
        for key in ("implied_volatility", "iv", "mid_iv"):
            if row.get(key) is not None:
                return float(row.get(key) or 0)
            if greeks.get(key) is not None:
                return float(greeks.get(key) or 0)
        return 0.0

    def _normalize_tradier_rows(self, symbol: str, rows: list[dict[str, Any]], expiry_type: str = "any") -> list[dict[str, Any]]:
        payloads: list[dict[str, Any]] = []
        for row in rows or []:
            payloads.append(
                {
                    "option_symbol": row.get("symbol") or row.get("option_symbol"),
                    "underlying": row.get("underlying") or symbol,
                    "option_type": row.get("option_type") or row.get("type"),
                    "strike": row.get("strike"),
                    "expiry": row.get("expiration_date") or row.get("expiry"),
                    "delta": self._extract_delta(row),
                    "implied_volatility": self._extract_iv(row),
                    "open_interest": row.get("open_interest") or row.get("openInterest") or 0,
                    "volume": row.get("volume") or 0,
                    "bid": row.get("bid") or 0,
                    "ask": row.get("ask") or 0,
                    "mark": row.get("mark") or 0,
                    "expiry_type": row.get("expiry_type") or expiry_type,
                }
            )
        return self.chain_service.normalize_contracts(symbol, payloads)

    def _derive_flow_rows(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        ranked = sorted(
            rows,
            key=lambda item: float(item.get("open_interest", 0) or 0) * max(float(item.get("mark", 0) or 0), 0.01),
            reverse=True,
        )
        flows: list[dict[str, Any]] = []
        for item in ranked[:12]:
            option_type = str(item.get("option_type") or "call").lower()
            flows.append(
                {
                    "option_symbol": item.get("option_symbol"),
                    "side": "call" if option_type == "call" else "put",
                    "premium": round(float(item.get("open_interest", 0) or 0) * float(item.get("mark", 0) or 0) * 100, 2),
                    "open_interest": item.get("open_interest", 0),
                    "mark": item.get("mark", 0),
                }
            )
        return flows

    async def refresh_chain(self, symbol: str, expiration: str | None = None) -> dict[str, Any]:
        if self.tradier_client is None:
            raise RuntimeError("Tradier client not configured")

        symbol = symbol.upper()
        rows = await self.tradier_client.get_options_chain(symbol=symbol, expiration=expiration, greeks=True)
        normalized = self._normalize_tradier_rows(symbol, rows)
        summary = self.chain_service.summarize_chain(normalized)
        payload = {
            "symbol": symbol,
            "expiration": expiration,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "rows": normalized,
            "summary": summary,
        }
        self.settings_repo.set_filter_override(self.CHAIN_KEY, payload)
        self.settings_repo.set_filter_override(self.FLOW_KEY, {"rows": self._derive_flow_rows(normalized)})
        return payload
