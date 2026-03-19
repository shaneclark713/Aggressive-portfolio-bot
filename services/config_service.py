from copy import deepcopy
from config.filter_presets import FILTER_PRESETS


class ConfigService:
    def __init__(self, settings_repo, settings):
        self.settings_repo = settings_repo
        self.settings = settings
        self.default_execution_mode = settings.bot_default_execution_mode

    def get_active_preset(self):
        return self.settings_repo.get_active_preset()

    def set_active_preset(self, preset_name: str):
        self.settings_repo.set_active_preset(preset_name)

    def get_execution_mode(self):
        return self.settings_repo.get_execution_mode() or self.default_execution_mode

    def set_execution_mode(self, mode: str):
        self.settings_repo.set_execution_mode(mode)

    def reset_execution_mode_on_boot(self):
        self.settings_repo.set_execution_mode(self.default_execution_mode)

    def get_strategy_states(self):
        defaults = {
            'Divergence': True,
            'Breakout Box': True,
            'Trend Following': True,
            'Mean Reversion': True,
        }
        return {**defaults, **self.settings_repo.get_strategy_states()}

    def resolve_filters(self):
        preset = deepcopy(FILTER_PRESETS[self.get_active_preset()])
        overrides = self.settings_repo.get_filter_overrides()
        for section, values in overrides.items():
            if section in preset and isinstance(values, dict):
                preset[section].update(values)
        return preset
