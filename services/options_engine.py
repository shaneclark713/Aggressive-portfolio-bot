from __future__ import annotations

from collections.abc import Mapping
from typing import Any


class OptionsEngine:
    def __init__(self, broker, data_service, config):
        self.broker = broker
        self.data = data_service
        self.config = config

    def _get_setting(self, key: str, default: Any = None) -> Any:
        if isinstance(self.config, Mapping):
            return self.config.get(key, default)
        getter = getattr(self.config, "get", None)
        if callable(getter):
            return getter(key, default)
        if hasattr(self.config, key):
            return getattr(self.config, key)
        return default

    async def execute(self, signal):
        symbol = signal["symbol"]
        expiration = signal.get("expiration")
        raw_chain = await self.data.get_chain(symbol, expiration=expiration)
        contracts = self.data.normalize(raw_chain, symbol=symbol)

        filtered = self.filter_contracts(contracts, signal)
        if not filtered:
            return None

        best = self.select_best(filtered)

        submit_order = getattr(self.broker, "submit_order", None)
        if callable(submit_order):
            return await submit_order(
                symbol=best["option_symbol"],
                qty=int(signal.get("qty", 1) or 1),
                side=signal.get("side", "buy"),
                type=signal.get("order_type", "market"),
                time_in_force=signal.get("time_in_force", "day"),
            )

        place_option_order = getattr(self.broker, "place_option_order", None)
        if callable(place_option_order):
            return await place_option_order(
                symbol=symbol,
                qty=int(signal.get("qty", 1) or 1),
                side=signal.get("side", "buy_to_open"),
                option_symbol=best["option_symbol"],
            )

        raise RuntimeError("Broker does not support options order submission")

    def filter_contracts(self, contracts, signal):
        delta_min = float(signal.get("delta_min", self._get_setting("delta_min", 0.3)) or 0.3)
        delta_max = float(signal.get("delta_max", self._get_setting("delta_max", 0.7)) or 0.7)
        min_oi = int(signal.get("min_open_interest", self._get_setting("min_open_interest", 100)) or 100)
        min_volume = int(signal.get("min_daily_volume", self._get_setting("min_daily_volume", 100)) or 100)
        contract_min_price = float(signal.get("contract_min_price", self._get_setting("contract_min_price", 0.5)) or 0.5)
        contract_max_price = float(signal.get("contract_max_price", self._get_setting("contract_max_price", 8.0)) or 8.0)
        option_type = str(signal.get("option_type", self._get_setting("option_type", "call")) or "call").lower()
        expiry_mode = str(signal.get("expiry_mode", self._get_setting("expiry_mode", "weekly")) or "weekly").lower()
        expiry_count = int(signal.get("expiry_count", self._get_setting("expiry_count", 1)) or 0)

        def contract_price(c):
            for key in ("mark", "last", "ask", "bid"):
                try:
                    value = c.get(key)
                    if value is not None and float(value) > 0:
                        return float(value)
                except Exception:
                    continue
            return 0.0

        def expiry_ok(c):
            dte = c.get("days_to_expiry")
            try:
                dte = int(dte)
            except Exception:
                return expiry_mode != "0dte"
            if expiry_mode == "0dte":
                return dte == 0
            if expiry_mode == "weekly":
                low = max((max(expiry_count, 1) - 1) * 7 + 1, 1)
                high = max(expiry_count, 1) * 7
                return low <= dte <= high
            if expiry_mode == "monthly":
                low = max((max(expiry_count, 1) - 1) * 30 + 1, 1)
                high = max(expiry_count, 1) * 31
                return low <= dte <= high
            return True

        filtered = []
        for c in contracts:
            if str(c.get("option_type", "call")).lower() != option_type:
                continue
            if int(c.get("volume", 0) or 0) < min_volume:
                continue
            if int(c.get("open_interest", 0) or 0) < min_oi:
                continue
            if abs(float(c.get("delta", 0) or 0)) < delta_min or abs(float(c.get("delta", 0) or 0)) > delta_max:
                continue
            price = contract_price(c)
            if price < contract_min_price or price > contract_max_price:
                continue
            if not expiry_ok(c):
                continue
            filtered.append(c)
        return filtered

    def select_best(self, contracts):
        contracts.sort(
            key=lambda x: (
                -int(x.get("volume", 0) or 0),
                -int(x.get("open_interest", 0) or 0),
                abs(abs(float(x.get("delta", 0) or 0)) - 0.5),
            )
        )
        return contracts[0]
