from __future__ import annotations

from copy import deepcopy
from typing import Any


class StrategyExecutionProfiles:
    MODE_ALIASES = {
        "alerts": "alerts_only",
        "alerts_only": "alerts_only",
        "approval_only": "paper",
        "paper": "paper",
        "automated": "live",
        "auto": "live",
        "live": "live",
    }
    STRATEGY_ALIASES = {
        "breakout box": "breakout_box",
        "breakout_box": "breakout_box",
        "divergence": "divergence",
        "trend following": "trend_following",
        "trend_following": "trend_following",
        "mean reversion": "mean_reversion",
        "mean_reversion": "mean_reversion",
        "options": "options_strategy",
        "options_strategy": "options_strategy",
    }
    DEFAULTS = {
        "alerts_only": {
            "__default__": {
                "risk_pct": 0.50,
                "atr_multiplier": 1.0,
                "ladder_steps": 3,
                "ladder_spacing_pct": 0.01,
                "trail_type": "percent",
                "trail_value": 0.02,
                "min_volume": 500000,
                "max_spread_pct": 0.03,
                "max_slippage_pct": 0.02,
                "position_mode": "auto",
                "paper_enabled": True,
                "live_enabled": False,
            },
        },
        "paper": {
            "__default__": {
                "risk_pct": 0.75,
                "atr_multiplier": 1.0,
                "ladder_steps": 3,
                "ladder_spacing_pct": 0.01,
                "trail_type": "percent",
                "trail_value": 0.02,
                "min_volume": 500000,
                "max_spread_pct": 0.03,
                "max_slippage_pct": 0.02,
                "position_mode": "auto",
                "paper_enabled": True,
                "live_enabled": False,
            },
            "trend_following": {
                "risk_pct": 0.60,
                "atr_multiplier": 1.25,
                "ladder_steps": 2,
            },
        },
        "live": {
            "__default__": {
                "risk_pct": 0.50,
                "atr_multiplier": 1.0,
                "ladder_steps": 3,
                "ladder_spacing_pct": 0.0075,
                "trail_type": "percent",
                "trail_value": 0.015,
                "min_volume": 1000000,
                "max_spread_pct": 0.02,
                "max_slippage_pct": 0.01,
                "position_mode": "auto",
                "paper_enabled": False,
                "live_enabled": True,
            },
            "breakout_box": {"ladder_steps": 4},
            "mean_reversion": {"atr_multiplier": 0.85},
            "trend_following": {"atr_multiplier": 1.35, "ladder_steps": 2},
        },
    }

    def __init__(self, settings_repo):
        self.settings_repo = settings_repo

    def normalize_mode(self, mode: str | None) -> str:
        raw = (mode or "alerts_only").strip().lower()
        return self.MODE_ALIASES.get(raw, "alerts_only")

    def normalize_strategy(self, strategy: str | None) -> str:
        raw = (strategy or "breakout_box").strip().lower().replace("-", " ").replace("_", " ")
        return self.STRATEGY_ALIASES.get(raw, raw.replace(" ", "_"))

    def display_strategy(self, strategy: str | None) -> str:
        normalized = self.normalize_strategy(strategy)
        return normalized.replace("_", " ").title()

    def _storage_key(self, mode: str, strategy: str) -> str:
        return f"execution_profile::{self.normalize_mode(mode)}::{self.normalize_strategy(strategy)}"

    def _base_profile(self, mode: str, strategy: str) -> dict[str, Any]:
        mode_key = self.normalize_mode(mode)
        strategy_key = self.normalize_strategy(strategy)
        base = deepcopy(self.DEFAULTS.get(mode_key, {}).get("__default__", {}))
        base.update(deepcopy(self.DEFAULTS.get(mode_key, {}).get(strategy_key, {})))
        return base

    def get_profile(self, mode: str, strategy: str) -> dict[str, Any]:
        mode_key = self.normalize_mode(mode)
        strategy_key = self.normalize_strategy(strategy)
        stored = self.settings_repo.get(self._storage_key(mode_key, strategy_key), {}) or {}
        profile = self._base_profile(mode_key, strategy_key)
        profile.update(stored if isinstance(stored, dict) else {})
        return profile

    def set_profile(self, mode: str, strategy: str, updates: dict[str, Any]) -> dict[str, Any]:
        mode_key = self.normalize_mode(mode)
        strategy_key = self.normalize_strategy(strategy)
        current = self.get_profile(mode_key, strategy_key)
        current.update(dict(updates or {}))
        self.settings_repo.set(self._storage_key(mode_key, strategy_key), current)
        return current
