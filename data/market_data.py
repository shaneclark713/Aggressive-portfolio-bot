from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Optional

import aiohttp
import pandas as pd


class PolygonMarketDataClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.polygon.io/v2"
        self.session: Optional[aiohttp.ClientSession] = None
        self.timeout = aiohttp.ClientTimeout(total=20)

    async def connect(self):
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(timeout=self.timeout)

    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()
        self.session = None

    def _ready(self) -> bool:
        return self.session is not None and not self.session.closed

    def _date_window(self, timespan: str) -> tuple[str, str]:
        end_dt = datetime.now(timezone.utc)

        if timespan == "minute":
            start_dt = end_dt - timedelta(days=2)
        elif timespan == "hour":
            start_dt = end_dt - timedelta(days=14)
        else:
            start_dt = end_dt - timedelta(days=365)

        return start_dt.date().isoformat(), end_dt.date().isoformat()

    def _default_limit(self, timespan: str) -> int:
        if timespan == "minute":
            return 1000
        if timespan == "hour":
            return 1500
        return 5000

    async def _request_json(self, endpoint: str, params: dict, retries: int = 3) -> dict:
        if not self._ready():
            raise RuntimeError("Polygon session not connected")

        last_error: Exception | None = None

        for attempt in range(retries):
            try:
                async with self.session.get(endpoint, params=params) as response:
                    if response.status == 429:
                        if attempt < retries - 1:
                            await asyncio.sleep(1.5 * (attempt + 1))
                            continue
                        raise RuntimeError("rate_limited")

                    if response.status >= 500:
                        if attempt < retries - 1:
                            await asyncio.sleep(1.0 * (attempt + 1))
                            continue
                        raise RuntimeError(f"polygon_http_{response.status}")

                    response.raise_for_status()
                    return await response.json()

            except aiohttp.ClientResponseError as exc:
                last_error = exc
                if exc.status == 429:
                    if attempt < retries - 1:
                        await asyncio.sleep(1.5 * (attempt + 1))
                        continue
                    raise RuntimeError("rate_limited") from exc
                raise RuntimeError(f"polygon_http_{exc.status}") from exc

            except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
                last_error = exc
                if attempt < retries - 1:
                    await asyncio.sleep(1.0 * (attempt + 1))
                    continue
                raise RuntimeError("polygon_request_failed") from exc

        raise RuntimeError("polygon_request_failed") from last_error

    async def get_historical_data(
        self,
        symbol: str,
        multiplier: int = 1,
        timespan: str = "day",
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> pd.DataFrame:
        if not start_date or not end_date:
            start_date, end_date = self._date_window(timespan)

        endpoint = f"{self.base_url}/aggs/ticker/{symbol}/range/{multiplier}/{timespan}/{start_date}/{end_date}"
        params = {
            "adjusted": "true",
            "sort": "asc",
            "limit": self._default_limit(timespan),
            "apiKey": self.api_key,
        }

        data = await self._request_json(endpoint, params=params)
        results = data.get("results", [])
        if not results:
            return pd.DataFrame()

        df = (
            pd.DataFrame(results)
            .rename(
                columns={
                    "v": "volume",
                    "vw": "vwap",
                    "o": "open",
                    "c": "close",
                    "h": "high",
                    "l": "low",
                    "t": "timestamp",
                    "n": "transactions",
                }
            )
        )

        df["datetime"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
        df = df.set_index("datetime").sort_index()

        required_columns = ["open", "high", "low", "close", "volume"]
        for column in required_columns:
            if column not in df.columns:
                df[column] = pd.NA

        return df

    async def get_latest_price(self, symbol: str):
        endpoint = f"{self.base_url}/snapshot/locale/us/markets/stocks/tickers/{symbol}"
        data = await self._request_json(endpoint, params={"apiKey": self.api_key})
        ticker = data.get("ticker", {})
        price = (ticker.get("lastTrade") or {}).get("p")
        if price is None:
            price = (ticker.get("min") or {}).get("c")
        return float(price) if price is not None else None
