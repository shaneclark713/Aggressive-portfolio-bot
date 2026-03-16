import pandas_ta as ta
class MarketRegimeClassifier:
    def classify(self, df):
        if len(df)<30: return 'UNKNOWN'
        work=df[['high','low','close']].dropna().copy(); work.ta.adx(length=14, append=True)
        adx=float(work.iloc[-1].get('ADX_14',0) or 0)
        return 'TREND' if adx>=20 else 'RANGE'
