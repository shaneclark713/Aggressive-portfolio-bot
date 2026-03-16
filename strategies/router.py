import pandas as pd
import pandas_ta as ta
from .breakout_box import BreakoutBoxStrategy
from .trend_following import TrendFollowingStrategy
from .divergence import DivergenceStrategy
from .mean_reversion import MeanReversionStrategy
from .market_regime import MarketRegimeClassifier
from risk.kill_switch import AntiFomoKillSwitch
from risk.risk_engine import RiskEngine

class StrategyRouter:
    def __init__(self, strategy_states=None):
        self.priority=['Divergence','Breakout Box','Trend Following','Mean Reversion']
        self.strategies={'Breakout Box':BreakoutBoxStrategy(),'Trend Following':TrendFollowingStrategy(),'Divergence':DivergenceStrategy(),'Mean Reversion':MeanReversionStrategy()}
        self.strategy_states=strategy_states or {name: True for name in self.strategies}
        self.regime=MarketRegimeClassifier(); self.kill_switch=AntiFomoKillSwitch(); self.risk_engine=RiskEngine(min_rr_ratio=2.0, atr_multiplier_sl=1.0)
    def _classify_trade_horizon(self, strategy_name, entry_price, take_profit, atr, rr_ratio):
        dist=abs(take_profit-entry_price); atr_mult=dist/atr if atr>0 else 0.0
        if strategy_name=='Mean Reversion': return 'DAY_TRADE'
        if strategy_name=='Trend Following': return 'SWING_TRADE'
        if strategy_name=='Breakout Box': return 'DAY_TRADE' if atr_mult<=1.5 and rr_ratio<=2.5 else 'SWING_TRADE'
        if strategy_name=='Divergence': return 'DAY_TRADE' if atr_mult<=1.25 else 'SWING_TRADE'
        return 'DAY_TRADE'
    def evaluate_ticker(self, symbol, df):
        req={'open','high','low','close','volume'}
        if df.empty or len(df)<50 or not req.issubset(df.columns): return None
        work=df[list(req)].dropna().copy(); regime=self.regime.classify(work); triggers=[]
        for name in self.priority:
            if not self.strategy_states.get(name, True): continue
            if name=='Mean Reversion' and regime != 'RANGE': continue
            result=self.strategies[name].analyze(work, symbol); signal=result.get('signal','WAIT')
            if signal.startswith('LONG_') or signal.startswith('SHORT_'): triggers.append((name,signal,result))
        if not triggers: return None
        winning_name, detected_signal, setup_data=triggers[0]; side='LONG' if detected_signal.startswith('LONG_') else 'SHORT'
        safe,_=self.kill_switch.check_trade_validity(work, symbol, side)
        if not safe: return None
        risk_df=work.copy(); risk_df.ta.atr(length=14, append=True); latest=risk_df.iloc[-1]; atr=latest.get('ATR_14')
        if pd.isna(atr) or float(atr)<=0: return None
        prior=risk_df.iloc[-21:-1]
        risk_data=self.risk_engine.calculate_trade_parameters(symbol=symbol, entry_price=float(latest['close']), side=side, atr=float(atr), recent_swing_high=float(prior['high'].max()), recent_swing_low=float(prior['low'].min()))
        if not risk_data.get('is_valid'): return None
        payload={'symbol':symbol,'strategy':winning_name,'all_triggers':[{'strategy':n,'signal':s} for n,s,_ in triggers],'signal':detected_signal,'side':side,'entry_price':risk_data['entry_price'],'stop_loss':risk_data['stop_loss'],'take_profit':risk_data['take_profit'],'risk_per_share':risk_data['risk'],'reward_per_share':risk_data['reward'],'rr_ratio':risk_data['actual_rr']}
        if winning_name=='Mean Reversion' and 'mean_target' in setup_data:
            mt=float(setup_data['mean_target'])
            if (side=='LONG' and mt>payload['entry_price']) or (side=='SHORT' and mt<payload['entry_price']):
                payload['take_profit']=round(mt,2); payload['reward_per_share']=round(abs(mt-payload['entry_price']),2); payload['rr_ratio']=round(payload['reward_per_share']/payload['risk_per_share'],2) if payload['risk_per_share'] else payload['rr_ratio']
        payload['trade_horizon']=self._classify_trade_horizon(winning_name,float(payload['entry_price']),float(payload['take_profit']),float(atr),float(payload['rr_ratio'])); payload['holding_style']='Intraday' if payload['trade_horizon']=='DAY_TRADE' else 'Multi-Day'; payload.update({k:v for k,v in setup_data.items() if k not in payload}); return payload
