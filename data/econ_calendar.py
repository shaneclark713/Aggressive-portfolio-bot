from __future__ import annotations

from datetime import date
import aiohttp


class FinnhubEconomicCalendarClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://finnhub.io/api/v1/calendar/economic"
        self.session = None
        self.timeout = aiohttp.ClientTimeout(total=15)

    async def connect(self):
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(timeout=self.timeout)

    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()
        self.session = None

    def _impact_label(self, raw_impact) -> str:
        if raw_impact is None:
            return "unknown"
        text = str(raw_impact).strip().lower()
        if text in {"high", "3", "three", "h"}:
            return "high"
        if text in {"medium", "2", "two", "m"}:
            return "medium"
        if text in {"low", "1", "one", "l"}:
            return "low"
        return text

    async def fetch_events(self, day: date) -> list[dict]:
        assert self.session is not None and not self.session.closed
        async with self.session.get(
            self.base_url,
            params={"from": day.isoformat(), "to": day.isoformat(), "token": self.api_key},
        ) as response:
            response.raise_for_status()
            data = await response.json()
            raw_events = data.get("economicCalendar", []) if isinstance(data, dict) else []

        enriched = []
        for event in raw_events:
            item = dict(event)
            item["impact_label"] = self._impact_label(item.get("impact"))
            item["event_name"] = item.get("event") or item.get("indicator") or "Unnamed event"
            item["event_time"] = item.get("time") or item.get("hour") or "TBD"
            item["country"] = item.get("country") or "US"
            enriched.append(item)

        impact_order = {"high": 0, "medium": 1, "low": 2, "unknown": 3}
        enriched.sort(key=lambda x: (impact_order.get(x.get("impact_label", "unknown"), 9), x.get("event_time", "ZZZ")))
        return enriched

    def summarize_events(self, events: list[dict], limit: int = 8) -> list[str]:
        return [
            f"{item.get('event_time', 'TBD')} | {item.get('impact_label', 'unknown').upper()} | {item.get('country', 'US')} | {item.get('event_name', 'Unnamed event')}"
            for item in events[:limit]
        ]

    def high_impact_events(self, events: list[dict]) -> list[dict]:
        return [item for item in events if item.get("impact_label") == "high"]
