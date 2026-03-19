from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict

from config.filter_presets import FILTER_PRESETS


class ConfigService:
    def __init__(self, settings_repo, settings):
        self.settings_repo = settings_repo
        self.settings = settings
        self.default_execution_mode = settings.bot_default_execution_mode

    def get_available_presets(self) -> Dict[str, Dict[str, Any]]:
        return deepcopy(FILTER_PRESETS)

    def get_active_preset(self) -> str:
        return self.settings_repo.get_active_preset()

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

    def toggle_strategy(self, strategy_name: str) -> bool:
        current = self.get_strategy_states().get(strategy_name, True)
        self.settings_repo.set_strategy_state(strategy_name, not current)
        return not current

    def resolve_filters(self) -> Dict[str, Any]:
        preset_name = self.get_active_preset()
        preset = deepcopy(FILTER_PRESETS[preset_name])
        overrides = self.settings_repo.get_filter_overrides()

        for section, values in overrides.items():
            if section in preset and isinstance(values, dict):
                preset[section].update(values)

        return preset

    def set_filter_override(self, section: str, key: str, value: Any) -> None:
        current = self.settings_repo.get_filter_overrides().get(section, {})
        if not isinstance(current, dict):
            current = {}
        current[key] = value
        self.settings_repo.set_filter_override(section, current)

    def get_human_summary(self) -> str:
        filters = self.resolve_filters()
        return (
            f"Preset: {self.get_active_preset()}\n"
            f"Mode: {self.get_execution_mode()}\n"
            f"Strategies Enabled: {sum(1 for state in self.get_strategy_states().values() if state)}\n"
            f"Filter Sections: {', '.join([k for k in filters.keys() if isinstance(filters[k], dict)])}"
        )
