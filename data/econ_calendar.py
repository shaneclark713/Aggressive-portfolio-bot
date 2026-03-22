from __future__ import annotations

from datetime import date

import aiohttp


HIGH_IMPACT_KEYWORDS = {"cpi", "ppi", "fed", "fomc", "powell", "jobs", "nonfarm", "payroll", "gdp", "pce", "rate"}


class FinnhubEconomicCalendarClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = 'https://finnhub.io/api/v1/calendar/economic'
        self.session = None
        self.timeout = aiohttp.ClientTimeout(total=15)

    async def connect(self):
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(timeout=self.timeout)

    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()
        self.session = None

    async def fetch_events(self, day: date) -> list[dict]:
        assert self.session is not None and not self.session.closed
        async with self.session.get(self.base_url, params={'from': day.isoformat(), 'to': day.isoformat(), 'token': self.api_key}) as r:
            r.raise_for_status()
            data = await r.json()
            events = data.get('economicCalendar', []) if isinstance(data, dict) else []
            for event in events:
                title = f"{event.get('event', '')} {event.get('country', '')}".lower()
                event['impact_label'] = 'high' if any(k in title for k in HIGH_IMPACT_KEYWORDS) else 'normal'
            return events
