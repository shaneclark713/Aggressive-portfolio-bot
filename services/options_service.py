from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, Iterable, Mapping


class OptionsService:
    DEFAULTS = {
        "enabled": False,
        "delta_min": 0.30,
        "delta_max": 0.70,
        "min_open_interest": 1000,
        "contract_min_price": 0.50,
        "contract_max_price": 8.00,
        "min_daily_volume": 100,
        "expiry_mode": "weekly",
        "expiry_count": 1,
        "chain_symbol": "SPY",
    }

    def __init__(self, settings_repo, config_service=None):
        self.settings_repo = settings_repo
        self.config_service = config_service

    def _normalize_expiry(self, settings: Mapping[str, Any]) -> Dict[str, Any]:
        current = deepcopy(dict(settings))
        expiry_mode = str(current.get("expiry_mode", current.get("expiry_preference", "weekly")) or "weekly").strip().lower()
        expiry_count = int(current.get("expiry_count", 1) or 0)

        if expiry_mode == "nearest":
            expiry_mode = "0dte"
            expiry_count = 0
        elif expiry_mode == "any":
            expiry_mode = "weekly"
        elif expiry_mode == "0dte":
            expiry_count = 0
        else:
            expiry_count = max(expiry_count, 1)

        current["expiry_mode"] = expiry_mode
        current["expiry_count"] = expiry_count
        return current

    def get_settings(self) -> Dict[str, Any]:
        merged = deepcopy(self.DEFAULTS)
        if hasattr(self.settings_repo, "get_options_settings"):
            merged.update(self.settings_repo.get_options_settings())
        else:
            stored = self.settings_repo.get("options_settings", {}) or {}
            merged.update(stored)
        return self._normalize_expiry(merged)

    def update_settings(self, **updates) -> Dict[str, Any]:
        current = self.get_settings()
        current.update(updates)
        current = self._normalize_expiry(current)
        if hasattr(self.settings_repo, "set_options_settings"):
            self.settings_repo.set_options_settings(current)
        else:
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

    def set_contract_price_range(self, min_price: float, max_price: float) -> Dict[str, Any]:
        if min_price < 0 or max_price <= 0 or min_price > max_price:
            raise ValueError("Contract price range is invalid")
        return self.update_settings(contract_min_price=round(min_price, 2), contract_max_price=round(max_price, 2))

    def set_min_daily_volume(self, value: int) -> Dict[str, Any]:
        if value < 0:
            raise ValueError("Min daily volume must be non-negative")
        return self.update_settings(min_daily_volume=int(value))

    def set_expiry(self, mode: str, count: int | None = None) -> Dict[str, Any]:
        mode = str(mode).strip().lower()
        if mode not in {"0dte", "weekly", "monthly"}:
            raise ValueError("Expiry mode must be 0dte, weekly, or monthly")
        count = 0 if mode == "0dte" else max(int(count or 1), 1)
        return self.update_settings(expiry_mode=mode, expiry_count=count)

    @staticmethod
    def _contract_price(contract: Mapping[str, Any]) -> float:
        for key in ("mark", "last", "ask", "bid"):
            try:
                value = contract.get(key)
                if value is not None and float(value) > 0:
                    return float(value)
            except Exception:
                continue
        return 0.0

    @staticmethod
    def _matches_expiry(contract: Mapping[str, Any], settings: Mapping[str, Any]) -> bool:
        mode = str(settings.get("expiry_mode", "weekly")).lower()
        count = int(settings.get("expiry_count", 1) or 0)
        dte = contract.get("days_to_expiry")
        try:
            dte_val = int(dte)
        except Exception:
            return mode != "0dte"

        if mode == "0dte":
            return dte_val == 0
        if mode == "weekly":
            low = max((count - 1) * 7 + 1, 1)
            high = count * 7
            return low <= dte_val <= high
        if mode == "monthly":
            low = max((count - 1) * 30 + 1, 1)
            high = count * 31
            return low <= dte_val <= high
        return True

    def filter_contracts(self, contracts: Iterable[dict]) -> list[dict]:
        settings = self.get_settings()
        filtered = []

        for contract in contracts or []:
            try:
                delta_value = abs(float(contract.get("delta", 0) or 0))
                oi = int(contract.get("open_interest", 0) or 0)
                volume = int(contract.get("volume", 0) or 0)
                price = self._contract_price(contract)
            except Exception:
                continue

            if delta_value < settings["delta_min"] or delta_value > settings["delta_max"]:
                continue
            if oi < settings["min_open_interest"]:
                continue
            if volume < settings["min_daily_volume"]:
                continue
            if price < settings["contract_min_price"] or price > settings["contract_max_price"]:
                continue
            if not self._matches_expiry(contract, settings):
                continue

            filtered.append(contract)

        return filtered
