from ib_insync import IB, Stock, Option, MarketOrder, LimitOrder, StopOrder
from .models import OrderRequest
import logging
import os

logger = logging.getLogger(__name__)


class IBKRClient:
    def __init__(self, host: str, port: int, client_id: int, account_id: str):
        self.host = host
        self.port = port
        self.client_id = client_id
        self.account_id = account_id
        self.ib = IB()

    async def connect(self):
        if self.ib.isConnected():
            return True

        broker_enabled = os.getenv("BROKER_ENABLED", "true").lower() == "true"
        allow_localhost = os.getenv("ALLOW_LOCALHOST_IB", "false").lower() == "true"

        if not broker_enabled:
            logger.info("IBKR connect skipped: BROKER_ENABLED is false")
            return False

        if self.host in {"127.0.0.1", "localhost"} and not allow_localhost:
            logger.warning(
                "IBKR connect skipped: host is %s but ALLOW_LOCALHOST_IB is false",
                self.host,
            )
            return False

        try:
            await self.ib.connectAsync(self.host, self.port, clientId=self.client_id)
            logger.info("IBKR connected to %s:%s clientId=%s", self.host, self.port, self.client_id)
            return True
        except Exception as exc:
            logger.exception("IBKR connection failed: %s", exc)
            return False

    async def close(self):
        if self.ib.isConnected():
            self.ib.disconnect()

    def is_connected(self):
        return self.ib.isConnected()

    async def get_positions(self):
        if not self.ib.isConnected():
            return []
        return list(self.ib.positions())

    async def close_positions(self, symbol=None, percent=None, quantity=None):
        if not self.ib.isConnected():
            raise RuntimeError("IBKR is not connected")

        actions = []
        for position in self.ib.positions():
            contract = position.contract
            if symbol and contract.symbol.upper() != symbol.upper():
                continue

            pos = float(position.position)
            if pos == 0:
                continue

            close_qty = abs(pos)
            if percent is not None:
                close_qty = max(1, int(abs(pos) * percent))
            if quantity is not None:
                close_qty = min(abs(pos), quantity)

            action = "SELL" if pos > 0 else "BUY"
            order = MarketOrder(action, close_qty, account=self.account_id)
            trade = self.ib.placeOrder(contract, order)
            actions.append(trade)

        return actions

    def _build_contract(self, req: OrderRequest):
        if req.instrument_type == "stock":
            return Stock(req.symbol, "SMART", "USD")
        if req.instrument_type == "option":
            return Option(
                req.symbol,
                req.option_expiry,
                req.option_strike,
                req.option_right,
                "SMART",
            )
        raise ValueError(f"Unsupported IBKR instrument type: {req.instrument_type}")

    async def place_order(self, req: OrderRequest):
        if not self.ib.isConnected():
            raise RuntimeError("IBKR is not connected")

        contract = self._build_contract(req)

        if req.order_type == "market":
            order = MarketOrder(req.side, req.quantity, account=self.account_id)
        elif req.order_type == "limit":
            order = LimitOrder(req.side, req.quantity, req.limit_price, account=self.account_id)
        elif req.order_type == "stop":
            order = StopOrder(req.side, req.quantity, req.stop_price, account=self.account_id)
        else:
            raise ValueError(f"Unsupported order type: {req.order_type}")

        return self.ib.placeOrder(contract, order)
