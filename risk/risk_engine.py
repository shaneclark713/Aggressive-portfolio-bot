class RiskEngine:
    def __init__(self, min_rr_ratio: float = 2.0, atr_multiplier_sl: float = 1.0): self.min_rr_ratio=min_rr_ratio; self.atr_multiplier_sl=atr_multiplier_sl
    def calculate_trade_parameters(self, symbol:str, entry_price:float, side:str, atr:float, recent_swing_high:float, recent_swing_low:float):
        side=side.upper()
        if any(v is None or v<=0 for v in [entry_price, atr, recent_swing_high, recent_swing_low]): return {'is_valid':False,'reason':'Invalid numeric inputs'}
        if recent_swing_low >= recent_swing_high: return {'is_valid':False,'reason':'Invalid swing structure'}
        if side=='LONG': stop=recent_swing_low-(atr*self.atr_multiplier_sl); take=recent_swing_high; risk=entry_price-stop; reward=take-entry_price
        elif side=='SHORT': stop=recent_swing_high+(atr*self.atr_multiplier_sl); take=recent_swing_low; risk=stop-entry_price; reward=entry_price-take
        else: return {'is_valid':False,'reason':'Invalid side'}
        if risk<=0: return {'is_valid':False,'reason':'Invalid risk math'}
        if reward<=0: return {'is_valid':False,'reason':'No logical structural reward'}
        rr=reward/risk; valid=rr>=self.min_rr_ratio
        return {'symbol':symbol,'side':side,'entry_price':round(entry_price,2),'stop_loss':round(stop,2),'take_profit':round(take,2),'risk':round(risk,2),'reward':round(reward,2),'actual_rr':round(rr,2),'is_valid':valid,'reason':'Passed' if valid else f'Poor structural R:R ({rr:.2f})'}
