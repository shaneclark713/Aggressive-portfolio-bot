from copy import deepcopy

from config.filters.descriptive import DESCRIPTIVE_FILTERS
from config.filters.fundamental import FUNDAMENTAL_FILTERS
from config.filters.technical import TECHNICAL_FILTERS


FILTER_PRESETS = {
    "day_trade_momentum": {
        "label": "Day Trade Momentum",
        "description": "Fast intraday setups with strong volume, trend confirmation, and catalyst protection.",
        "descriptive": {
            **deepcopy(DESCRIPTIVE_FILTERS),
            "price_min": 15.0,
            "avg_daily_volume_min": 3_000_000,
            "avg_dollar_volume_min": 75_000_000,
            "optionable_only": True,
        },
        "fundamental": {
            **deepcopy(FUNDAMENTAL_FILTERS),
            "exclude_upcoming_earnings_within_days": 1,
            "require_news_catalyst": False,
        },
        "technical": {
            **deepcopy(TECHNICAL_FILTERS),
            "atr_min_pct": 0.025,
            "adx_min": 23,
            "volume_vs_average_min_ratio": 1.75,
            "premarket_gap_max_pct": 12.0,
            "max_extension_from_ema9_pct": 3.5,
            "minimum_rr_ratio": 2.0,
        },
    },
    "swing_trade_structural": {
        "label": "Swing Trade Structural",
        "description": "Multi-day setups with cleaner structure and stricter event risk controls.",
        "descriptive": {
            **deepcopy(DESCRIPTIVE_FILTERS),
            "price_min": 20.0,
            "avg_daily_volume_min": 1_500_000,
            "avg_dollar_volume_min": 40_000_000,
            "optionable_only": True,
        },
        "fundamental": {
            **deepcopy(FUNDAMENTAL_FILTERS),
            "exclude_upcoming_earnings_within_days": 3,
            "exclude_recent_earnings_within_days": 2,
            "require_positive_revenue_growth": False,
            "require_positive_eps_growth": False,
        },
        "technical": {
            **deepcopy(TECHNICAL_FILTERS),
            "atr_min_pct": 0.018,
            "adx_min": 18,
            "volume_vs_average_min_ratio": 1.2,
            "premarket_gap_max_pct": 8.0,
            "max_extension_from_ema9_pct": 6.0,
            "minimum_rr_ratio": 2.25,
        },
    },
}
