import pandas as pd
from strategies.router import StrategyRouter

def test_router_callable():
    df=pd.DataFrame({'open':[1]*60,'high':[1.1]*60,'low':[0.9]*60,'close':[1]*60,'volume':[1000]*60})
    StrategyRouter().evaluate_ticker('SPY', df)
