from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, Iterable


class OptionsService:
    DEFAULTS = {
        "enabled": False,
        "delta_min": 0.30,
        "delta_max": 0.70,
        "min_open_interest": 1000,
        "min_daily_volume": 250,
        "contract_min_price": 0.10,
        "contract_max_price": 10.0,
        "expiry_mode": "weekly",
        "expiry_value": 1,
        "chain_symbol": "SPY",
    }

    def __init__(self, settings_repo):
        self.settings_repo = settings_repo

    def _normalize(self, payload: Dict[str, Any] | None) -> Dict[str, Any]:
        payload = dict(payload or {})
        if "expiry_mode" not in payload:
            legacy = str(payload.get("expiry_preference") or "weekly").lower().strip()
            payload["expiry_mode"] = "0dte" if legacy == "nearest" else legacy
        if "expiry_value" not in payload:
            payload["expiry_value"] = 0 if payload.get("expiry_mode") == "0dte" else 1
        merged = dict(self.DEFAULTS)
        merged.update(payload)
        merged["expiry_mode"] = str(merged.get("expiry_mode") or "weekly").lower().strip()
        if merged["expiry_mode"] not in {"0dte", "weekly", "monthly"}:
            merged["expiry_mode"] = "weekly"
        merged["expiry_value"] = 0 if merged["expiry_mode"] == "0dte" else max(int(merged.get("expiry_value", 1) or 1), 1)
        return merged

    def get_settings(self) -> Dict[str, Any]:
        stored = self.settings_repo.get("options_settings", {}) or {}
        return self._normalize(stored)

    def update_settings(self, **updates) -> Dict[str, Any]:
        current = self.get_settings()
        current.update(updates)
        current = self._normalize(current)
        self.settings_repo.set("options_settings", current)
        return current

    def toggle_enabled(self, enabled: bool = True) -> Dict[str, Any]:
        return self.update_settings(enabled=bool(enabled))

    def set_delta_range(self, delta_min: float, delta_max: float) -> Dict[str, Any]:
        if delta_min < 0 or delta_max > 1 or delta_min >= delta_max:
            raise ValueError("Delta range must be between 0 and 1, with min < max")
        return self.update_settings(delta_min=round(delta_min, 2), delta_max=round(delta_max, 2))

    def set_min_open_interest(self, value: int) -> Dict[str, Any]:
        if value < 0:
            raise ValueError("Open interest must be non-negative")
        return self.update_settings(min_open_interest=int(value))

    def set_expiry(self, mode: str, value: int | None = None) -> Dict[str, Any]:
        mode = str(mode or "weekly").lower().strip()
        if mode not in {"0dte", "weekly", "monthly"}:
            raise ValueError("Expiry must be 0dte, weekly, or monthly")
        if mode == "0dte":
            value = 0
        else:
            value = max(int(value or 1), 1)
        return self.update_settings(expiry_mode=mode, expiry_value=value)

    def set_expiry_preference(self, value: str) -> Dict[str, Any]:
        mode = "0dte" if str(value).lower().strip() == "nearest" else str(value).lower().strip()
        return self.set_expiry(mode, 1 if mode in {"weekly", "monthly"} else 0)

    def _days_to_expiry(self, contract: dict) -> int | None:
        raw = contract.get("days_to_expiry")
        if raw is not None:
            try:
                return int(raw)
            except Exception:
                pass
        expiry = contract.get("expiry") or contract.get("expiration_date")
        if not expiry:
            return None
        text = str(expiry)
        for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S%z"):
            try:
                parsed = datetime.strptime(text, fmt)
                return (parsed.date() - date.today()).days
            except Exception:
                continue
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
            return (parsed.date() - date.today()).days
        except Exception:
            return None

    def _matches_expiry(self, contract: dict, settings: Dict[str, Any]) -> bool:
        mode = settings.get("expiry_mode", "weekly")
        value = int(settings.get("expiry_value", 1) or 1)
        days = self._days_to_expiry(contract)
        if days is None:
            return True
        if mode == "0dte":
            return days <= 0
        if mode == "weekly":
            lower = 0 if value <= 1 else 7 * (value - 1) + 1
            upper = 7 * value
            return lower <= days <= upper
        if mode == "monthly":
            lower = 0 if value <= 1 else 30 * (value - 1) + 1
            upper = 31 * value
            return lower <= days <= upper
        return True

    def filter_contracts(self, contracts: Iterable[dict]) -> list[dict]:
        settings = self.get_settings()
        filtered = []

        for contract in contracts or []:
            delta = contract.get("delta")
            oi = int(contract.get("open_interest", 0) or 0)
            volume = int(contract.get("volume", 0) or 0)
            mark = float(contract.get("mark", 0) or 0)

            try:
                delta_value = abs(float(delta))
            except Exception:
                continue

            if delta_value < settings["delta_min"] or delta_value > settings["delta_max"]:
                continue
            if oi < settings["min_open_interest"]:
                continue
            if volume < settings["min_daily_volume"]:
                continue
            if mark < float(settings["contract_min_price"]):
                continue
            if mark > float(settings["contract_max_price"]):
                continue
            if not self._matches_expiry(contract, settings):
                continue

            filtered.append(contract)

        return filtered
