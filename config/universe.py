CORE_EQUITIES = [
    'SPY','QQQ','IWM','DIA',
    'TSLA','NVDA','AMD','AAPL','META','MSFT','AMZN','GOOGL','NFLX','AVGO','PLTR',
    'SMCI','MU','INTC','ARM','TSM','BABA','COIN','MSTR','SOFI','HOOD','RIVN','NIO',
    'XOM','CVX','XLE','JPM','BAC','GS','XLF','UNH','LLY','XBI','XLV'
]
CORE_FUTURES = ['MES','MNQ','MYM','M2K']
EXCLUDED_TICKERS = []
DAY_TRADE_SETTINGS = {
    'min_price': 10.0,
    'min_avg_daily_volume': 1_500_000,
    'min_relative_volume': 1.1,
    'min_atr_pct': 0.015,
    'max_gap_pct': 0.20,
}
SWING_TRADE_SETTINGS = {
    'min_price': 10.0,
    'min_avg_daily_volume': 1_000_000,
    'min_relative_volume': 1.0,
    'min_atr_pct': 0.012,
    'max_gap_pct': 0.15,
}
