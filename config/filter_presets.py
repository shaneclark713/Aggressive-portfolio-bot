from copy import deepcopy

from config.filters.descriptive import DESCRIPTIVE_FILTERS
from config.filters.fundamental import FUNDAMENTAL_FILTERS
from config.filters.options import OPTIONS_FILTERS
from config.filters.technical import TECHNICAL_FILTERS


def _descriptive_defaults():
    base = deepcopy(DESCRIPTIVE_FILTERS)
    base.setdefault("max_float", 500_000_000)
    base.setdefault("min_premarket_vol", 100_000)
    base.setdefault("premarket_gap_min_percent", 1.0)
    base.setdefault("shortlist_cap", 8)
    return base


def _options_defaults(expiry_mode: str, expiry_count: int, contract_max_price: float) -> dict:
    base = deepcopy(OPTIONS_FILTERS)
    base.update(
        {
            "enabled": True,
            "expiry_mode": expiry_mode,
            "expiry_count": expiry_count,
            "contract_max_price": contract_max_price,
        }
    )
    return base


FILTER_PRESETS = {
    "day_trade_momentum": {
        "label": "Overall / Day Trade Momentum",
        "description": "Fast intraday setups with strong volume, trend confirmation, and catalyst protection.",
        "descriptive": {**_descriptive_defaults(), "price_min": 15.0, "avg_daily_volume_min": 3_000_000, "avg_dollar_volume_min": 75_000_000, "optionable_only": True, "max_float": 500_000_000, "min_premarket_vol": 250_000, "premarket_gap_min_percent": 1.5, "shortlist_cap": 8},
        "fundamental": {**deepcopy(FUNDAMENTAL_FILTERS), "exclude_upcoming_earnings_within_days": 1, "require_news_catalyst": False},
        "technical": {**deepcopy(TECHNICAL_FILTERS), "atr_min_pct": 0.025, "adx_min": 23, "volume_vs_average_min_ratio": 1.75, "premarket_gap_max_pct": 12.0, "max_extension_from_ema9_pct": 3.5, "minimum_rr_ratio": 2.0},
        "options": _options_defaults("weekly", 1, 8.0),
    },
    "premarket_gap_focus": {
        "label": "Premarket Gap Focus",
        "description": "Focused on premarket movers with real volume and overnight catalysts.",
        "descriptive": {**_descriptive_defaults(), "price_min": 5.0, "avg_daily_volume_min": 1_000_000, "avg_dollar_volume_min": 15_000_000, "optionable_only": False, "max_float": 750_000_000, "min_premarket_vol": 300_000, "premarket_gap_min_percent": 2.0, "shortlist_cap": 6},
        "fundamental": {**deepcopy(FUNDAMENTAL_FILTERS), "exclude_upcoming_earnings_within_days": 0, "require_news_catalyst": False},
        "technical": {**deepcopy(TECHNICAL_FILTERS), "atr_min_pct": 0.02, "adx_min": 18, "volume_vs_average_min_ratio": 1.25, "premarket_gap_max_pct": 20.0, "max_extension_from_ema9_pct": 8.0, "minimum_rr_ratio": 1.75},
        "options": _options_defaults("weekly", 1, 6.0),
    },
    "midday_trend": {
        "label": "Midday Trend",
        "description": "Cleaner midday continuation and VWAP-style trend structure.",
        "descriptive": {**_descriptive_defaults(), "price_min": 15.0, "avg_daily_volume_min": 2_000_000, "avg_dollar_volume_min": 50_000_000, "optionable_only": True, "max_float": 1_500_000_000, "min_premarket_vol": 0, "premarket_gap_min_percent": 0.0, "shortlist_cap": 8},
        "fundamental": {**deepcopy(FUNDAMENTAL_FILTERS), "exclude_upcoming_earnings_within_days": 1, "require_news_catalyst": False},
        "technical": {**deepcopy(TECHNICAL_FILTERS), "atr_min_pct": 0.018, "adx_min": 20, "volume_vs_average_min_ratio": 1.1, "premarket_gap_max_pct": 15.0, "max_extension_from_ema9_pct": 5.0, "minimum_rr_ratio": 1.8},
        "options": _options_defaults("weekly", 1, 7.5),
    },
    "overnight_catalyst": {
        "label": "Overnight Catalyst",
        "description": "Tomorrow-bias prep using daily structure, news, and swing-quality liquidity.",
        "descriptive": {**_descriptive_defaults(), "price_min": 10.0, "avg_daily_volume_min": 1_000_000, "avg_dollar_volume_min": 25_000_000, "optionable_only": True, "max_float": 2_000_000_000, "min_premarket_vol": 0, "premarket_gap_min_percent": 0.0, "shortlist_cap": 10},
        "fundamental": {**deepcopy(FUNDAMENTAL_FILTERS), "exclude_upcoming_earnings_within_days": 2, "exclude_recent_earnings_within_days": 1, "require_positive_revenue_growth": False, "require_positive_eps_growth": False, "require_news_catalyst": False},
        "technical": {**deepcopy(TECHNICAL_FILTERS), "atr_min_pct": 0.015, "adx_min": 16, "volume_vs_average_min_ratio": 1.0, "premarket_gap_max_pct": 25.0, "max_extension_from_ema9_pct": 8.0, "minimum_rr_ratio": 2.0},
        "options": _options_defaults("monthly", 1, 12.0),
    },
    "swing_trade_structural": {
        "label": "Swing Trade Structural",
        "description": "Multi-day setups with cleaner structure and stricter event risk controls.",
        "descriptive": {**_descriptive_defaults(), "price_min": 20.0, "avg_daily_volume_min": 1_500_000, "avg_dollar_volume_min": 40_000_000, "optionable_only": True, "max_float": 1_500_000_000, "min_premarket_vol": 50_000, "premarket_gap_min_percent": 0.5, "shortlist_cap": 8},
        "fundamental": {**deepcopy(FUNDAMENTAL_FILTERS), "exclude_upcoming_earnings_within_days": 3, "exclude_recent_earnings_within_days": 2, "require_positive_revenue_growth": False, "require_positive_eps_growth": False},
        "technical": {**deepcopy(TECHNICAL_FILTERS), "atr_min_pct": 0.018, "adx_min": 18, "volume_vs_average_min_ratio": 1.2, "premarket_gap_max_pct": 8.0, "max_extension_from_ema9_pct": 6.0, "minimum_rr_ratio": 2.25},
        "options": _options_defaults("monthly", 1, 15.0),
    },
}
