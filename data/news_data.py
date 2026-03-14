import aiohttp
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger("aggressive_portfolio_bot.data.news_data")


class NewsScraper:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://finnhub.io/api/v1"
        self.session: Optional[aiohttp.ClientSession] = None
        self.timeout = aiohttp.ClientTimeout(total=15)

    async def connect(self) -> None:
        """Create a reusable aiohttp session."""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(timeout=self.timeout)

    async def close(self) -> None:
        """Close the aiohttp session."""
        if self.session and not self.session.closed:
            await self.session.close()
        self.session = None

    def _is_ready(self) -> bool:
        return self.session is not None and not self.session.closed

    async def fetch_market_news(self, category: str = "general") -> List[Dict[str, Any]]:
        """
        Fetch latest market news.
        Valid categories typically include: general, forex, crypto, merger.
        """
        if not self._is_ready():
            logger.warning("NewsScraper session is not initialized.")
            return []

        endpoint = f"{self.base_url}/news"
        params = {
            "category": category,
            "token": self.api_key,
        }

        try:
            async with self.session.get(endpoint, params=params) as response:
                if response.status != 200:
                    logger.warning("Failed to fetch market news. Status=%s", response.status)
                    return []

                data = await response.json()
                if not isinstance(data, list):
                    logger.warning("Unexpected market news payload type: %s", type(data).__name__)
                    return []

                logger.info("Fetched %s market news articles.", len(data))
                return data

        except Exception as e:
            logger.exception("Error fetching market news: %s", e)
            return []

    async def fetch_ticker_news(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
    ) -> List[Dict[str, Any]]:
        """
        Fetch ticker-specific news.
        Dates should be YYYY-MM-DD.
        """
        if not self._is_ready():
            logger.warning("NewsScraper session is not initialized.")
            return []

        endpoint = f"{self.base_url}/company-news"
        params = {
            "symbol": symbol,
            "from": start_date,
            "to": end_date,
            "token": self.api_key,
        }

        try:
            async with self.session.get(endpoint, params=params) as response:
                if response.status != 200:
                    logger.warning(
                        "Failed to fetch ticker news for %s. Status=%s",
                        symbol,
                        response.status,
                    )
                    return []

                data = await response.json()
                if not isinstance(data, list):
                    logger.warning(
                        "Unexpected ticker news payload for %s: %s",
                        symbol,
                        type(data).__name__,
                    )
                    return []

                logger.info("Fetched %s news articles for %s.", len(data), symbol)
                return data

        except Exception as e:
            logger.exception("Error fetching news for %s: %s", symbol, e)
            return []

    def analyze_sentiment(self, headlines: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Lightweight keyword-based sentiment score.
        """
        bullish_keywords = ["surge", "beat", "upgraded", "record", "growth", "jump", "rally"]
        bearish_keywords = ["missed", "downgraded", "plunge", "lawsuit", "inflation", "drop", "fear"]

        bullish_count = 0
        bearish_count = 0

        for article in headlines:
            headline = article.get("headline", "").lower()

            if any(word in headline for word in bullish_keywords):
                bullish_count += 1
            if any(word in headline for word in bearish_keywords):
                bearish_count += 1

        total_scored = bullish_count + bearish_count
        if total_scored == 0:
            return {
                "sentiment": "Neutral",
                "score": 0.0,
                "bullish_articles": 0,
                "bearish_articles": 0,
            }

        net_score = (bullish_count - bearish_count) / total_scored

        if net_score > 0.3:
            sentiment = "Bullish"
        elif net_score < -0.3:
            sentiment = "Bearish"
        else:
            sentiment = "Neutral"

        return {
            "sentiment": sentiment,
            "score": round(net_score, 4),
            "bullish_articles": bullish_count,
            "bearish_articles": bearish_count,
        }
