import logging
from typing import Optional, Dict, Any

import pyotp
import robin_stocks.robinhood as r

logger = logging.getLogger("aggressive_portfolio_bot.brokers.robinhood")


class RobinhoodClient:
    def __init__(
        self,
        username: str,
        password: str,
        mfa_secret: Optional[str] = None,
        store_session: bool = False,
    ):
        self.username = username
        self.password = password
        self.mfa_secret = mfa_secret
        self.store_session = store_session
        self.is_authenticated = False

    def login(self) -> bool:
        """Authenticate with Robinhood."""
        logger.info("Attempting Robinhood authentication...")
        try:
            mfa_code = None
            by_sms = True

            if self.mfa_secret:
                mfa_code = pyotp.TOTP(self.mfa_secret).now()
                by_sms = False  # Prefer TOTP when secret is available

            response = r.login(
                username=self.username,
                password=self.password,
                expiresIn=86400,
                by_sms=by_sms,
                mfa_code=mfa_code,
                store_session=self.store_session,
            )

            if isinstance(response, dict) and response.get("access_token"):
                self.is_authenticated = True
                logger.info("Successfully authenticated with Robinhood.")
                return True

            logger.error("Robinhood login did not return an access token: %s", response)
            self.is_authenticated = False
            return False

        except Exception as e:
            logger.exception("Robinhood login failed: %s", e)
            self.is_authenticated = False
            return False

    def get_active_positions(self) -> Dict[str, Any]:
        """Fetch current open stock and option positions."""
        if not self.is_authenticated:
            logger.warning("Cannot fetch positions: not authenticated.")
            return {"stocks": [], "options": []}

        try:
            stocks = r.get_open_stock_positions() or []
            options = r.get_open_option_positions() or []
            return {"stocks": stocks, "options": options}
        except Exception as e:
            logger.exception("Error fetching Robinhood positions: %s", e)
            return {"stocks": [], "options": []}

    def get_latest_price(self, symbol: str) -> Optional[float]:
        """Fetch the latest price for a ticker."""
        try:
            quotes = r.get_latest_price(symbol)
            if not quotes:
                return None

            raw_price = quotes[0]
            if raw_price in (None, ""):
                return None

            return float(raw_price)
        except (TypeError, ValueError) as e:
            logger.error("Invalid price format for %s: %s", symbol, e)
            return None
        except Exception as e:
            logger.exception("Error fetching price for %s: %s", symbol, e)
            return None

    def logout(self) -> None:
        """Safely close the Robinhood session."""
        try:
            r.logout()
            logger.info("Logged out of Robinhood.")
        except Exception as e:
            logger.exception("Robinhood logout failed: %s", e)
        finally:
            self.is_authenticated = False
