from risk.risk_engine import RiskEngine

def test_risk_engine_has_result():
    data=RiskEngine().calculate_trade_parameters('SPY', 100, 'LONG', 2, 110, 90)
    assert 'is_valid' in data
