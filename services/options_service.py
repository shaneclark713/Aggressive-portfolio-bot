from __future__ import annotations

from typing import Any, Dict, Iterable


class OptionsService:
    DEFAULTS = {
        "enabled": False,
        "delta_min": 0.30,
        "delta_max": 0.70,
        "min_open_interest": 1000,
        "expiry_preference": "weekly",
    }

    def __init__(self, settings_repo):
        self.settings_repo = settings_repo

    def get_settings(self) -> Dict[str, Any]:
        merged = dict(self.DEFAULTS)
        stored = self.settings_repo.get("options_settings", {}) or {}
        merged.update(stored)
        return merged

    def update_settings(self, **updates) -> Dict[str, Any]:
        current = self.get_settings()
        current.update(updates)
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

    def set_expiry_preference(self, value: str) -> Dict[str, Any]:
        value = value.lower().strip()
        if value not in {"weekly", "monthly", "any"}:
            raise ValueError("Expiry must be weekly, monthly, or any")
        return self.update_settings(expiry_preference=value)

    def filter_contracts(self, contracts: Iterable[dict]) -> list[dict]:
        settings = self.get_settings()
        filtered = []

        for contract in contracts or []:
            delta = contract.get("delta")
            oi = int(contract.get("open_interest", 0) or 0)
            expiry_type = str(contract.get("expiry_type", "any")).lower()

            try:
                delta_value = abs(float(delta))
            except Exception:
                continue

            if delta_value < settings["delta_min"] or delta_value > settings["delta_max"]:
                continue
            if oi < settings["min_open_interest"]:
                continue
            if settings["expiry_preference"] != "any" and expiry_type != settings["expiry_preference"]:
                continue

            filtered.append(contract)

        return filtered
