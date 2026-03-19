from config.filters.descriptive import DESCRIPTIVE_FILTERS
from config.filters.fundamental import FUNDAMENTAL_FILTERS
from config.filters.technical import TECHNICAL_FILTERS

FILTER_PRESETS = {
    "day_trade_momentum": {
        "descriptive": DESCRIPTIVE_FILTERS,
        "fundamental": FUNDAMENTAL_FILTERS,
        "technical": TECHNICAL_FILTERS,
    },
    "swing_trade": {
        "descriptive": DESCRIPTIVE_FILTERS,
        "fundamental": FUNDAMENTAL_FILTERS,
        "technical": TECHNICAL_FILTERS,
    },
}
