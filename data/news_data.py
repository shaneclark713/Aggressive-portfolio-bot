from __future__ import annotations

import asyncio
import logging
from datetime import date, timedelta
from typing import Optional

import aiohttp

logger = logging.getLogger("aggressive_portfolio_bot.data.news_data")


class FinnhubNewsClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://finnhub.io/api/v1"
        self.session: Optional[aiohttp.ClientSession] = None
        self.timeout = aiohttp.ClientTimeout(total=15)

    async def connect(self):
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(timeout=self.timeout)

    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()
        self.session = None

    def _ready(self) -> bool:
        return self.session is not None and not self.session.closed

    async def _get_json(self, path: str, params: dict):
        if not self._ready():
            raise RuntimeError("Finnhub session not connected")
        try:
            async with self.session.get(f"{self.base_url}/{path}", params=params) as response:
                if response.status in {401, 403, 429}:
                    body = await response.text()
                    logger.warning("Finnhub news unavailable. path=%s status=%s body=%s", path, response.status, body[:300])
                    return []
                response.raise_for_status()
                data = await response.json()
                return data if isinstance(data, list) else []
        except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
            logger.warning("Finnhub news request failed for %s: %s", path, exc)
            return []

    async def fetch_market_news(self, category: str = "general") -> list[dict]:
        return await self._get_json("news", {"category": category, "token": self.api_key})

    async def fetch_ticker_news(self, symbol: str, start_date: str | None = None, end_date: str | None = None) -> list[dict]:
        today = date.today()
        if end_date is None:
            end_date = today.isoformat()
        if start_date is None:
            start_date = (today - timedelta(days=3)).isoformat()
        return await self._get_json("company-news", {"symbol": symbol, "from": start_date, "to": end_date, "token": self.api_key})

    def summarize_headlines(self, headlines: list[dict], limit: int = 5) -> list[str]:
        bullets = []
        for item in headlines[:limit]:
            headline = item.get("headline") or item.get("title") or "Untitled headline"
            source = item.get("source") or "Unknown source"
            bullets.append(f"{headline} [{source}]")
        return bullets
