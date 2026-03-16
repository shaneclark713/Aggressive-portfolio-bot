TECH_QQQ_BENCHMARK_SYMBOLS = {'AAPL','AMD','AMZN','GOOGL','INTC','META','MSFT','NFLX','NVDA','QQQ','SMCI','TSLA'}

def benchmark_for_symbol(symbol: str) -> str:
    return 'QQQ' if symbol.upper() in TECH_QQQ_BENCHMARK_SYMBOLS else 'SPY'
