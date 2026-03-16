import backtrader as bt

class SandboxAnalyzer(bt.Analyzer):
    def create_analysis(self): self.rets={'total_trades':0,'wins':0,'losses':0,'win_rate_pct':0.0,'net_pnl':0.0}
    def notify_trade(self, trade):
        if trade.isclosed:
            self.rets['total_trades']+=1; self.rets['net_pnl']+=trade.pnlcomm
            if trade.pnlcomm>0: self.rets['wins']+=1
            else: self.rets['losses']+=1
    def get_analysis(self):
        total=self.rets['total_trades']; self.rets['win_rate_pct']=round((self.rets['wins']/total*100) if total else 0.0,2); self.rets['net_pnl']=round(self.rets['net_pnl'],2); return self.rets

class BacktestEngine:
    def __init__(self): self.cerebro=bt.Cerebro()
    def run_historical_probability(self, strategy_class, df):
        if df.empty or not {'open','high','low','close','volume'}.issubset(df.columns): return {}
        feed=bt.feeds.PandasData(dataname=df.copy().sort_index(), datetime=None, open='open', high='high', low='low', close='close', volume='volume', openinterest=None)
        self.cerebro=bt.Cerebro(); self.cerebro.adddata(feed); self.cerebro.addstrategy(strategy_class); self.cerebro.broker.setcash(10000.0); self.cerebro.addanalyzer(SandboxAnalyzer, _name='sandbox_stats')
        results=self.cerebro.run(); return results[0].analyzers.sandbox_stats.get_analysis() if results else {}
