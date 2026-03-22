from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

import aiohttp


class FinnhubNewsClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = 'https://finnhub.io/api/v1'
        self.session: Optional[aiohttp.ClientSession] = None
        self.timeout = aiohttp.ClientTimeout(total=15)

    async def connect(self):
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(timeout=self.timeout)

    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()
        self.session = None

    def _ready(self):
        return self.session is not None and not self.session.closed

    async def fetch_market_news(self, category: str = 'general') -> list[dict]:
        if not self._ready():
            raise RuntimeError('Finnhub session not connected')
        async with self.session.get(f'{self.base_url}/news', params={'category': category, 'token': self.api_key}) as r:
            r.raise_for_status()
            data = await r.json()
            return data if isinstance(data, list) else []

    async def fetch_ticker_news(self, symbol: str, start_date: str | None = None, end_date: str | None = None) -> list[dict]:
        if not self._ready():
            raise RuntimeError('Finnhub session not connected')
        now = datetime.now(timezone.utc).date()
        if not end_date:
            end_date = now.isoformat()
        if not start_date:
            start_date = (now - timedelta(days=3)).isoformat()
        async with self.session.get(f'{self.base_url}/company-news', params={'symbol': symbol, 'from': start_date, 'to': end_date, 'token': self.api_key}) as r:
            r.raise_for_status()
            data = await r.json()
            return data if isinstance(data, list) else []
