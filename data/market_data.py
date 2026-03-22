from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

import aiohttp
import pandas as pd


class PolygonMarketDataClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = 'https://api.polygon.io/v2'
        self.session: Optional[aiohttp.ClientSession] = None
        self.timeout = aiohttp.ClientTimeout(total=20)

    async def connect(self):
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(timeout=self.timeout)

    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()
        self.session = None

    def _ready(self):
        return self.session is not None and not self.session.closed

    def _date_window(self, timespan: str) -> tuple[str, str]:
        end_dt = datetime.now(timezone.utc)
        if timespan == 'minute':
            start_dt = end_dt - timedelta(days=10)
        elif timespan == 'hour':
            start_dt = end_dt - timedelta(days=30)
        else:
            start_dt = end_dt - timedelta(days=365)
        return start_dt.date().isoformat(), end_dt.date().isoformat()

    async def get_historical_data(self, symbol: str, multiplier: int = 1, timespan: str = 'day', start_date: str | None = None, end_date: str | None = None) -> pd.DataFrame:
        if not self._ready():
            raise RuntimeError('Polygon session not connected')
        if not start_date or not end_date:
            start_date, end_date = self._date_window(timespan)
        endpoint = f'{self.base_url}/aggs/ticker/{symbol}/range/{multiplier}/{timespan}/{start_date}/{end_date}'
        async with self.session.get(endpoint, params={'adjusted': 'true', 'sort': 'asc', 'limit': 5000, 'apiKey': self.api_key}) as r:
            r.raise_for_status()
            data = await r.json()
            results = data.get('results', [])
            if not results:
                return pd.DataFrame()
            df = pd.DataFrame(results).rename(columns={'v': 'volume', 'vw': 'vwap', 'o': 'open', 'c': 'close', 'h': 'high', 'l': 'low', 't': 'timestamp', 'n': 'transactions'})
            df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
            return df.set_index('datetime').sort_index()

    async def get_latest_price(self, symbol: str):
        if not self._ready():
            raise RuntimeError('Polygon session not connected')
        async with self.session.get(f'{self.base_url}/snapshot/locale/us/markets/stocks/tickers/{symbol}', params={'apiKey': self.api_key}) as r:
            r.raise_for_status()
            data = await r.json()
            ticker = data.get('ticker', {})
            price = (ticker.get('lastTrade') or {}).get('p')
            if price is None:
                price = (ticker.get('min') or {}).get('c')
            return float(price) if price is not None else None
