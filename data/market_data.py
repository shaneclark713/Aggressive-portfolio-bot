from __future__ import annotations
import aiohttp, pandas as pd
from typing import Optional

class PolygonMarketDataClient:
    def __init__(self, api_key: str):
        self.api_key=api_key; self.base_url='https://api.polygon.io/v2'; self.session: Optional[aiohttp.ClientSession]=None; self.timeout=aiohttp.ClientTimeout(total=20)
    async def connect(self):
        if self.session is None or self.session.closed: self.session=aiohttp.ClientSession(timeout=self.timeout)
    async def close(self):
        if self.session and not self.session.closed: await self.session.close(); self.session=None
    def _ready(self): return self.session is not None and not self.session.closed
    async def get_historical_data(self, symbol:str, multiplier:int=1, timespan:str='day', start_date:str='2025-01-01', end_date:str='2026-12-31') -> pd.DataFrame:
        if not self._ready(): raise RuntimeError('Polygon session not connected')
        endpoint=f'{self.base_url}/aggs/ticker/{symbol}/range/{multiplier}/{timespan}/{start_date}/{end_date}'
        async with self.session.get(endpoint, params={'adjusted':'true','sort':'asc','apiKey':self.api_key}) as r:
            r.raise_for_status(); data=await r.json(); results=data.get('results',[])
            if not results: return pd.DataFrame()
            df=pd.DataFrame(results).rename(columns={'v':'volume','vw':'vwap','o':'open','c':'close','h':'high','l':'low','t':'timestamp','n':'transactions'})
            df['datetime']=pd.to_datetime(df['timestamp'], unit='ms', utc=True)
            return df.set_index('datetime').sort_index()
    async def get_latest_price(self, symbol:str):
        if not self._ready(): raise RuntimeError('Polygon session not connected')
        async with self.session.get(f'{self.base_url}/snapshot/locale/us/markets/stocks/tickers/{symbol}', params={'apiKey':self.api_key}) as r:
            r.raise_for_status(); data=await r.json(); ticker=data.get('ticker',{}); price=(ticker.get('lastTrade') or {}).get('p')
            if price is None: price=(ticker.get('min') or {}).get('c')
            return float(price) if price is not None else None
