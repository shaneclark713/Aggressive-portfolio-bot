import pandas_ta as ta

class AntiFomoKillSwitch:
    def __init__(self): self.max_ema_extension_pct=0.03; self.rsi_boiling_point=80; self.elevator_candle_count=4; self.atr_blowoff_multiplier=3.0; self.volume_spike_multiplier=2.0
    def check_trade_validity(self, df, symbol:str, side:str='LONG'):
        if side.upper() != 'LONG': return True, 'Passed (Not a Long Entry)'
        req={'open','high','low','close','volume'}
        if len(df)<21 or not req.issubset(df.columns): return False, 'Insufficient data for FOMO indicators'
        work=df[list(req)].copy(); work.ta.ema(length=9, append=True); work.ta.rsi(length=14, append=True); work.ta.bbands(length=20, std=2, append=True); work.ta.atr(length=14, append=True)
        latest=work.iloc[-1]; close=float(latest['close']); high=float(latest['high']); low=float(latest['low']); volume=float(latest['volume']); ema=float(latest.get('EMA_9', close)); rsi=float(latest.get('RSI_14', 50)); upper=float(latest.get('BBU_20_2.0', close*1.5)); atr=float(latest.get('ATR_14', 1.0)); avg_volume=work['volume'].rolling(window=20).mean().iloc[-1]
        if ema>0 and (close-ema)/ema > self.max_ema_extension_pct: return False, 'Rubber Band Extension'
        if rsi > self.rsi_boiling_point and close > upper: return False, 'Boiling Point Exhaustion'
        if (high-low) > (atr*self.atr_blowoff_multiplier) and volume > (avg_volume*self.volume_spike_multiplier): return False, 'Blow-Off Top Reversal Risk'
        consecutive=0
        for i in range(1,self.elevator_candle_count+1):
            row=work.iloc[-i]; o=float(row['open']); c=float(row['close']); h=float(row['high']); l=float(row['low']); rng=h-l
            if c>o and rng>0 and ((h-c)/rng)<=0.30: consecutive+=1
            else: break
        if consecutive>=self.elevator_candle_count: return False, 'Elevator Parabolic Move'
        return True, 'Setup Valid'
