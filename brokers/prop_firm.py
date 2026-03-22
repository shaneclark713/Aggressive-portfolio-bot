import aiohttp
import logging
from typing import Optional, Dict, Any, List

logger = logging.getLogger("aggressive_portfolio_bot.brokers.prop_firm")


class PropFirmClient:
    def __init__(self, api_key: str, api_secret: str, base_url: str):
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url.rstrip("/")
        self.token: Optional[str] = None
        self.session: Optional[aiohttp.ClientSession] = None
        self.timeout = aiohttp.ClientTimeout(total=15)

    async def connect(self) -> bool:
        """Establish an async session and authenticate."""
        try:
            if self.session is None or self.session.closed:
                self.session = aiohttp.ClientSession(timeout=self.timeout)

            auth_url = f"{self.base_url}/auth/accesstokenrequest"
            payload = {
                "name": self.api_key,
                "password": self.api_secret,
                "appVersion": "1.0",
            }

            async with self.session.post(auth_url, json=payload) as response:
                if response.status != 200:
                    logger.error("Prop Firm auth failed with status %s", response.status)
                    return False

                data = await response.json()
                access_token = data.get("accessToken")
                if not access_token:
                    logger.error("Prop Firm auth response missing accessToken: %s", data)
                    return False

                self.token = access_token
                logger.info("Successfully authenticated with Prop Firm API.")
                return True

        except Exception as e:
            logger.exception("Connection/auth error to Prop Firm: %s", e)
            return False

    def _is_ready(self) -> bool:
        return bool(self.token and self.session and not self.session.closed)

    def _auth_headers(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self.token}"}

    async def get_dom_data(self, symbol: str) -> Dict[str, Any]:
        """Fetch DOM data for a futures contract."""
        if not self._is_ready():
            logger.warning("Cannot fetch DOM: client not authenticated or session unavailable.")
            return {}

        endpoint = f"{self.base_url}/marketdata/getdom"

        try:
            async with self.session.get(
                endpoint,
                headers=self._auth_headers(),
                params={"symbol": symbol},
            ) as response:
                if response.status == 200:
                    return await response.json()

                logger.warning("Failed to fetch DOM for %s. Status=%s", symbol, response.status)
                return {}

        except Exception as e:
            logger.exception("Error fetching DOM for %s: %s", symbol, e)
            return {}

    async def get_active_orders(self) -> List[Dict[str, Any]]:
        """Fetch currently working orders."""
        if not self._is_ready():
            logger.warning("Cannot fetch active orders: client not authenticated or session unavailable.")
            return []

        endpoint = f"{self.base_url}/order/list"

        try:
            async with self.session.get(endpoint, headers=self._auth_headers()) as response:
                if response.status == 200:
                    data = await response.json()
                    return data if isinstance(data, list) else []

                logger.warning("Failed to fetch active orders. Status=%s", response.status)
                return []

        except Exception as e:
            logger.exception("Error fetching active orders: %s", e)
            return []

    async def close(self) -> None:
        """Safely close the async session."""
        try:
            if self.session and not self.session.closed:
                await self.session.close()
                logger.info("Closed Prop Firm API session.")
        except Exception as e:
            logger.exception("Error closing Prop Firm session: %s", e)
        finally:
            self.session = None
            self.token = None
