from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, Iterable

from config.filter_presets import FILTER_PRESETS


class ConfigService:
    VALID_FILTER_CATEGORIES = ("descriptive", "fundamental", "technical")

    def __init__(self, settings_repo, settings):
        self.settings_repo = settings_repo
        self.settings = settings
        self.default_execution_mode = settings.bot_default_execution_mode

    def get_active_preset(self) -> str:
        preset = self.settings_repo.get_active_preset()
        return preset if preset in FILTER_PRESETS else "day_trade_momentum"

    def set_active_preset(self, preset_name: str) -> None:
        if preset_name not in FILTER_PRESETS:
            raise ValueError(f"Unknown preset: {preset_name}")
        self.settings_repo.set_active_preset(preset_name)

    def get_execution_mode(self) -> str:
        return self.settings_repo.get_execution_mode() or self.default_execution_mode

    def set_execution_mode(self, mode: str) -> None:
        self.settings_repo.set_execution_mode(mode)

    def reset_execution_mode_on_boot(self) -> None:
        self.settings_repo.set_execution_mode(self.default_execution_mode)

    def get_strategy_states(self) -> Dict[str, bool]:
        defaults = {
            "Divergence": True,
            "Breakout Box": True,
            "Trend Following": True,
            "Mean Reversion": True,
        }
        return {**defaults, **self.settings_repo.get_strategy_states()}

    def list_filter_categories(self) -> Iterable[str]:
        return self.VALID_FILTER_CATEGORIES

    def resolve_filters(self) -> Dict[str, Dict[str, Any]]:
        preset = deepcopy(FILTER_PRESETS[self.get_active_preset()])
        overrides = self.settings_repo.get_filter_overrides()

        for override_key, override_value in overrides.items():
            if "." not in override_key:
                continue
            category, field = override_key.split(".", 1)
            category = category.lower()
            if category not in self.VALID_FILTER_CATEGORIES:
                continue
            if category not in preset or not isinstance(preset[category], dict):
                preset[category] = {}
            preset[category][field] = override_value

        return {
            category: preset.get(category, {})
            for category in self.VALID_FILTER_CATEGORIES
        }

    def get_filter_category(self, category: str) -> Dict[str, Any]:
        category = category.lower()
        self._ensure_valid_category(category)
        return self.resolve_filters().get(category, {})

    def get_filter_fields(self, category: str) -> Dict[str, Any]:
        category = category.lower()
        return self.get_filter_category(category)

    def get_filter_value(self, category: str, field: str) -> Any:
        category = category.lower()
        self._ensure_valid_category(category)

        filters = self.resolve_filters()
        if field not in filters.get(category, {}):
            raise ValueError(f"Unknown filter field: {category}.{field}")

        return filters[category][field]

    def set_filter_value(self, category: str, field: str, raw_value: str) -> Any:
        category = category.lower()
        self._ensure_valid_category(category)

        filters = self.resolve_filters()
        if field not in filters[category]:
            raise ValueError(f"Unknown filter field: {category}.{field}")

        current_value = filters[category][field]
        parsed_value = self._coerce_value(raw_value, current_value)
        self._validate_filter_value(category, field, parsed_value)
        self.settings_repo.set_filter_override(f"{category}.{field}", parsed_value)
        return parsed_value

    def reset_filter_category(self, category: str) -> None:
        category = category.lower()
        self._ensure_valid_category(category)

        overrides = self.settings_repo.get_filter_overrides()
        prefix = f"{category}."
        for override_key in list(overrides.keys()):
            if override_key.startswith(prefix):
                self.settings_repo.clear_filter_override(override_key)

    def reset_all_filter_overrides(self) -> None:
        overrides = self.settings_repo.get_filter_overrides()
        for override_key in list(overrides.keys()):
            self.settings_repo.clear_filter_override(override_key)

    def _ensure_valid_category(self, category: str) -> None:
        if category not in self.VALID_FILTER_CATEGORIES:
            raise ValueError(f"Unknown filter category: {category}")

    def _coerce_value(self, raw_value: str, current_value: Any) -> Any:
        raw = raw_value.strip()

        if isinstance(current_value, bool):
            lowered = raw.lower()
            if lowered in {"true", "1", "yes", "on"}:
                return True
            if lowered in {"false", "0", "no", "off"}:
                return False
            raise ValueError("Expected boolean: true/false")

        if isinstance(current_value, int) and not isinstance(current_value, bool):
            return int(raw)

        if isinstance(current_value, float):
            return float(raw)

        return raw

    def _validate_filter_value(self, category: str, field: str, value: Any) -> None:
        if field.endswith("_min") or field.endswith("_max"):
            if isinstance(value, (int, float)) and value < 0:
                raise ValueError(f"{field} must be non-negative")

        if field == "price_max" and value <= 0:
            raise ValueError("price_max must be greater than 0")

        if field == "price_min" and value < 0:
            raise ValueError("price_min must be non-negative")

        if field == "atr_min_pct" and not (0 <= value <= 1):
            raise ValueError("atr_min_pct must be between 0 and 1")

        if field == "max_gap_pct" and not (0 <= value <= 1):
            raise ValueError("max_gap_pct must be between 0 and 1")

        if field == "max_short_float_pct" and not (0 <= value <= 100):
            raise ValueError("max_short_float_pct must be between 0 and 100")

        if field == "adx_min" and value < 0:
            raise ValueError("adx_min must be non-negative")

        if field == "relative_strength_lookback_minutes" and int(value) <= 0:
            raise ValueError("relative_strength_lookback_minutes must be greater than 0")

        if field == "volume_vs_average_min_ratio" and float(value) <= 0:
            raise ValueError("volume_vs_average_min_ratio must be greater than 0")
