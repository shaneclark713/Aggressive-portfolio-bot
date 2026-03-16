import pandas as pd
from risk.kill_switch import AntiFomoKillSwitch

def test_kill_switch_returns_tuple():
    df=pd.DataFrame({'open':[1]*25,'high':[1.1]*25,'low':[0.9]*25,'close':[1]*25,'volume':[100]*25})
    result=AntiFomoKillSwitch().check_trade_validity(df,'SPY','LONG')
    assert isinstance(result, tuple)
