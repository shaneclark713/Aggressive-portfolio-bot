from copy import deepcopy
from config.filters.descriptive import DESCRIPTIVE_FILTERS
from config.filters.fundamental import FUNDAMENTAL_FILTERS
from config.filters.technical import TECHNICAL_FILTERS

def _base() -> dict:
    return {'descriptive': deepcopy(DESCRIPTIVE_FILTERS), 'fundamental': deepcopy(FUNDAMENTAL_FILTERS), 'technical': deepcopy(TECHNICAL_FILTERS)}

FILTER_PRESETS = {
    'day_trade_momentum': {**_base(), 'descriptive': {**_base()['descriptive'], 'option_short': 'Optionable', 'average_volume': 'Over 3M', 'relative_volume': 'Over 1.5', 'price': 'Over $20'}, 'technical': {**_base()['technical'], 'volatility': 'Over 3%', 'average_true_range': 'Over 1', 'rsi_14': '40 to 75', 'gap': 'Up 1% to 10%'}},
    'swing_trend': {**_base(), 'descriptive': {**_base()['descriptive'], 'option_short': 'Optionable', 'average_volume': 'Over 1M', 'price': 'Over $15'}, 'fundamental': {**_base()['fundamental'], 'eps_growth_qtr_over_qtr': 'Over 20%', 'sales_growth_qtr_over_qtr': 'Over 20%', 'return_on_equity': 'Over 15%'}, 'technical': {**_base()['technical'], 'sma_20': 'Price above SMA20', 'sma_50': 'Price above SMA50', 'sma_200': 'Price above SMA200', 'rsi_14': '45 to 70'}},
    'mean_reversion': {**_base(), 'descriptive': {**_base()['descriptive'], 'option_short': 'Optionable', 'average_volume': 'Over 2M', 'price': 'Over $20'}, 'technical': {**_base()['technical'], 'rsi_14': 'Under 35', 'average_true_range': 'Over 1'}},
    'news_breakout': {**_base(), 'descriptive': {**_base()['descriptive'], 'option_short': 'Optionable', 'average_volume': 'Over 3M', 'relative_volume': 'Over 2', 'price': 'Over $20'}, 'fundamental': {**_base()['fundamental'], 'earnings_and_revenue_surprise': 'Positive (>0%)'}, 'technical': {**_base()['technical'], 'volatility': 'Over 4%', 'average_true_range': 'Over 1', 'gap': 'Up 1%'}},
}
