from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List

from config.filter_presets import FILTER_PRESETS


class ConfigService:
    def __init__(self, settings_repo, settings):
        self.settings_repo = settings_repo
        self.settings = settings
        self.default_execution_mode = settings.bot_default_execution_mode

    def get_active_preset(self) -> str:
        return self.settings_repo.get_active_preset()

    def get_available_presets(self) -> List[str]:
        return list(FILTER_PRESETS.keys())

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

    def resolve_filters(self) -> Dict[str, Dict[str, Any]]:
        active_preset = self.get_active_preset()
        if active_preset not in FILTER_PRESETS:
            active_preset = next(iter(FILTER_PRESETS))
        preset = deepcopy(FILTER_PRESETS[active_preset])

        overrides = self.settings_repo.get_filter_overrides()
        for section, values in overrides.items():
            if section in preset and isinstance(values, dict):
                preset[section].update(values)
        return preset

    def get_filter_categories(self) -> List[str]:
        return list(self.resolve_filters().keys())

    def get_filter_fields(self, category: str) -> Dict[str, Any]:
        filters = self.resolve_filters()
        if category not in filters or not isinstance(filters[category], dict):
            raise ValueError(f"Unknown filter category: {category}")
        return filters[category]

    def get_filter_value(self, category: str, field: str) -> Any:
        values = self.get_filter_fields(category)
        if field not in values:
            raise ValueError(f"Unknown filter field: {category}.{field}")
        return values[field]

    def set_filter_value(self, category: str, field: str, raw_value: str) -> Any:
        current_value = self.get_filter_value(category, field)
        parsed_value = self._parse_value_like(current_value, raw_value)

        overrides = self.settings_repo.get_filter_overrides()
        category_overrides = overrides.get(category, {})
        if not isinstance(category_overrides, dict):
            category_overrides = {}

        category_overrides[field] = parsed_value
        self.settings_repo.set_filter_override(category, category_overrides)
        return parsed_value

    def reset_filter_overrides(self, category: str | None = None, field: str | None = None) -> None:
        if category is None:
            for section in self.get_filter_categories():
                self.settings_repo.clear_filter_override(section)
            return

        if field is None:
            self.settings_repo.clear_filter_override(category)
            return

        overrides = self.settings_repo.get_filter_overrides()
        category_overrides = overrides.get(category, {})
        if not isinstance(category_overrides, dict):
            return

        if field in category_overrides:
            category_overrides.pop(field, None)

        if category_overrides:
            self.settings_repo.set_filter_override(category, category_overrides)
        else:
            self.settings_repo.clear_filter_override(category)

    def _parse_value_like(self, current_value: Any, raw_value: str) -> Any:
        value = raw_value.strip()

        if isinstance(current_value, bool):
            lowered = value.lower()
            if lowered in {"true", "1", "yes", "y", "on"}:
                return True
            if lowered in {"false", "0", "no", "n", "off"}:
                return False
            raise ValueError("Enter true or false.")

        if isinstance(current_value, int) and not isinstance(current_value, bool):
            try:
                return int(value)
            except ValueError as exc:
                raise ValueError("Enter a whole number.") from exc

        if isinstance(current_value, float):
            try:
                return float(value)
            except ValueError as exc:
                raise ValueError("Enter a number.") from exc

        return value
