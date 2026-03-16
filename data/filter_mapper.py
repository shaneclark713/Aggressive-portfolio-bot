from copy import deepcopy
from config.filter_presets import FILTER_PRESETS
class FilterMapper:
    def get_preset(self, preset_name:str) -> dict:
        if preset_name not in FILTER_PRESETS: raise ValueError(f'Unknown preset: {preset_name}')
        return deepcopy(FILTER_PRESETS[preset_name])
    def flatten_preset(self, preset_name:str) -> dict:
        preset=self.get_preset(preset_name); flat={}
        for section, values in preset.items():
            for key, value in values.items(): flat[f'{section}.{key}']=value
        return flat
