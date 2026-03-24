from __future__ import annotations
from copy import deepcopy
from typing import Any, Dict, Iterable, List
from config.filter_presets import FILTER_PRESETS

class ConfigService:
    VALID_FILTER_CATEGORIES = ("descriptive", "fundamental", "technical")
    FILTER_PROFILES = ("overall", "premarket", "midday", "overnight")
    DEFAULT_PROFILE_PRESETS = {"overall":"day_trade_momentum","premarket":"premarket_gap_focus","midday":"midday_trend","overnight":"overnight_catalyst"}

    def __init__(self, settings_repo, settings):
        self.settings_repo = settings_repo
        self.settings = settings
        self.default_execution_mode = settings.bot_default_execution_mode

    def _meta_key(self, key:str)->str: return f"__meta__.{key}"
    def _get_overrides(self)->Dict[str,Any]: return self.settings_repo.get_filter_overrides()
    def get_available_presets(self)->List[str]: return list(FILTER_PRESETS.keys())
    def get_filter_profiles(self)->List[str]: return list(self.FILTER_PROFILES)
    def get_active_preset(self)->str: return self.get_profile_preset("overall")
    def set_active_preset(self,preset_name:str)->None: self.set_profile_preset("overall", preset_name)

    def get_active_filter_profile(self)->str:
        value = self._get_overrides().get(self._meta_key("active_filter_profile"), "overall")
        return value if value in self.FILTER_PROFILES else "overall"

    def set_active_filter_profile(self, profile:str)->None:
        if profile not in self.FILTER_PROFILES: raise ValueError(f"Unknown filter profile: {profile}")
        self.settings_repo.set_filter_override(self._meta_key("active_filter_profile"), profile)

    def get_profile_preset(self, profile:str)->str:
        if profile not in self.FILTER_PROFILES: raise ValueError(f"Unknown filter profile: {profile}")
        value = self._get_overrides().get(self._meta_key(f"profile_preset.{profile}"), self.DEFAULT_PROFILE_PRESETS[profile])
        return value if value in FILTER_PRESETS else self.DEFAULT_PROFILE_PRESETS[profile]

    def set_profile_preset(self, profile:str, preset_name:str)->None:
        if profile not in self.FILTER_PROFILES: raise ValueError(f"Unknown filter profile: {profile}")
        if preset_name not in FILTER_PRESETS: raise ValueError(f"Unknown preset: {preset_name}")
        self.settings_repo.set_filter_override(self._meta_key(f"profile_preset.{profile}"), preset_name)

    def get_profile_preset_map(self)->Dict[str,str]: return {p:self.get_profile_preset(p) for p in self.FILTER_PROFILES}
    def get_execution_mode(self)->str: return self.settings_repo.get_execution_mode() or self.default_execution_mode
    def set_execution_mode(self, mode:str)->None: self.settings_repo.set_execution_mode(mode)
    def reset_execution_mode_on_boot(self)->None: self.settings_repo.set_execution_mode(self.default_execution_mode)

    def get_strategy_states(self)->Dict[str,bool]:
        defaults={"Divergence":True,"Breakout Box":True,"Trend Following":True,"Mean Reversion":True}
        return {**defaults, **self.settings_repo.get_strategy_states()}

    def list_filter_categories(self)->Iterable[str]: return self.VALID_FILTER_CATEGORIES

    def resolve_filters(self, profile:str|None=None)->Dict[str,Dict[str,Any]]:
        profile = profile or self.get_active_filter_profile()
        preset = deepcopy(FILTER_PRESETS[self.get_profile_preset(profile)])
        for override_key, override_value in self._get_overrides().items():
            if override_key.startswith("__meta__."): continue
            target_profile=None; category_field=override_key
            if override_key.count(".")>=2:
                profile_candidate, maybe_category, _ = override_key.split(".",2)
                if profile_candidate in self.FILTER_PROFILES and maybe_category in self.VALID_FILTER_CATEGORIES:
                    target_profile=profile_candidate; category_field=override_key[len(profile_candidate)+1:]
            if target_profile is not None and target_profile != profile: continue
            if "." not in category_field: continue
            category, field = category_field.split(".",1)
            if category not in self.VALID_FILTER_CATEGORIES: continue
            preset.setdefault(category,{})[field]=override_value
        return {c:preset.get(c,{}) for c in self.VALID_FILTER_CATEGORIES}

    def get_filter_category(self, category:str, profile:str|None=None)->Dict[str,Any]:
        category=category.lower(); self._ensure_valid_category(category); return self.resolve_filters(profile).get(category,{})
    def get_filter_fields(self, category:str, profile:str|None=None)->Dict[str,Any]: return self.get_filter_category(category, profile)
    def get_filter_value(self, category:str, field:str, profile:str|None=None)->Any:
        filters=self.resolve_filters(profile); category=category.lower(); self._ensure_valid_category(category)
        if field not in filters.get(category, {}): raise ValueError(f"Unknown filter field: {category}.{field}")
        return filters[category][field]
    def set_filter_value(self, category:str, field:str, raw_value:str, profile:str|None=None)->Any:
        profile=profile or self.get_active_filter_profile(); category=category.lower(); self._ensure_valid_category(category)
        filters=self.resolve_filters(profile)
        if field not in filters[category]: raise ValueError(f"Unknown filter field: {category}.{field}")
        current_value=filters[category][field]; parsed=self._coerce_value(raw_value, current_value); self._validate_filter_value(category, field, parsed)
        self.settings_repo.set_filter_override(f"{profile}.{category}.{field}", parsed); return parsed
    def reset_filter_category(self, category:str, profile:str|None=None)->None:
        profile=profile or self.get_active_filter_profile(); category=category.lower(); self._ensure_valid_category(category)
        for key in list(self._get_overrides().keys()):
            if key.startswith(f"{profile}.{category}."): self.settings_repo.clear_filter_override(key)
    def reset_filter_overrides(self, category:str|None=None, profile:str|None=None)->None:
        profile=profile or self.get_active_filter_profile()
        if category is not None: self.reset_filter_category(category, profile); return
        for key in list(self._get_overrides().keys()):
            if key.startswith(f"{profile}."): self.settings_repo.clear_filter_override(key)
    def reset_all_filter_overrides(self)->None:
        for profile in self.FILTER_PROFILES: self.reset_filter_overrides(profile=profile)
    def _ensure_valid_category(self, category:str)->None:
        if category not in self.VALID_FILTER_CATEGORIES: raise ValueError(f"Unknown filter category: {category}")
    def _coerce_value(self, raw_value:str, current_value:Any)->Any:
        raw=raw_value.strip()
        if isinstance(current_value,bool):
            lowered=raw.lower()
            if lowered in {"true","1","yes","on"}: return True
            if lowered in {"false","0","no","off"}: return False
            raise ValueError("Expected boolean: true/false")
        if isinstance(current_value,int) and not isinstance(current_value,bool): return int(raw.replace(",",""))
        if isinstance(current_value,float): return float(raw.replace(",",""))
        if isinstance(current_value,list): return [i.strip() for i in raw.split(",") if i.strip()]
        return raw
    def _validate_filter_value(self, category:str, field:str, value:Any)->None:
        if field.endswith("_min") or field.endswith("_max"):
            if isinstance(value,(int,float)) and value < 0: raise ValueError(f"{field} must be non-negative")
        if field in {"price_max","avg_daily_volume_min","avg_dollar_volume_min","relative_strength_lookback_minutes","minimum_rr_ratio","volume_vs_average_min_ratio","max_float","shortlist_cap"} and isinstance(value,(int,float)) and value <= 0:
            raise ValueError(f"{field} must be greater than 0")
        if field in {"atr_min_pct","max_extension_from_ema9_pct","premarket_gap_max_pct","premarket_gap_min_percent","max_short_float_pct"} and isinstance(value,(int,float)) and value < 0:
            raise ValueError(f"{field} must be non-negative")
        if field == "price_min" and value < 0: raise ValueError("price_min must be non-negative")
        if field == "min_premarket_vol" and value < 0: raise ValueError("min_premarket_vol must be non-negative")
