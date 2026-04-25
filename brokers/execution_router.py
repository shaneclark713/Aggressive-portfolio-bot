from __future__ import annotations

from typing import Any, Dict


class ModeAwareAlpacaProxy:
    """Small proxy used by services that only need current-mode Alpaca reads."""

    def __init__(self, router: "ExecutionRouter"):
        self.router = router

    async def get_positions(self, symbol: str | None = None) -> list[dict]:
        client = self.router.get_alpaca_client(order=False)
        if client is None:
            return []
        return await client.get_positions(symbol=symbol)


class ModeAwareTradierProxy:
    """Small proxy used by services that need current-mode Tradier reads."""

    def __init__(self, router: "ExecutionRouter"):
        self.router = router

    async def get_expirations(self, symbol: str) -> list[str]:
        client = self.router.get_tradier_market_data_client()
        if client is None:
            return []
        return await client.get_expirations(symbol)

    async def get_options_chain(self, symbol: str, expiration: str | None = None, greeks: bool = True):
        client = self.router.get_tradier_market_data_client()
        if client is None:
            return []
        return await client.get_options_chain(symbol=symbol, expiration=expiration, greeks=greeks)

    async def get_positions(self) -> list[dict]:
        client = self.router.get_tradier_client(order=False)
        if client is None:
            return []
        return await client.get_positions()


class ExecutionRouter:
    def __init__(
        self,
        alpaca_client=None,
        tradier_client=None,
        config_service=None,
        alpaca_paper_client=None,
        alpaca_live_client=None,
        tradier_paper_client=None,
        tradier_live_client=None,
    ):
        # Legacy single clients are kept as fallbacks for older deployments.
        self.alpaca_client = alpaca_client
        self.tradier_client = tradier_client
        self.config_service = config_service

        # Mode-specific clients are what Telegram Mode should use.
        self.alpaca_paper_client = alpaca_paper_client
        self.alpaca_live_client = alpaca_live_client
        self.tradier_paper_client = tradier_paper_client
        self.tradier_live_client = tradier_live_client

    def alpaca_proxy(self) -> ModeAwareAlpacaProxy:
        return ModeAwareAlpacaProxy(self)

    def tradier_proxy(self) -> ModeAwareTradierProxy:
        return ModeAwareTradierProxy(self)

    def _mode(self) -> str:
        if self.config_service is None:
            return "alerts_only"
        if hasattr(self.config_service, "get_execution_mode"):
            return str(self.config_service.get_execution_mode() or "alerts_only").lower()
        if isinstance(self.config_service, dict):
            return str(self.config_service.get("mode", "alerts_only") or "alerts_only").lower()
        return "alerts_only"

    def _is_alerts_only(self) -> bool:
        return self._mode() in {"alerts", "alert", "alerts_only", "off"}

    def _is_paper(self) -> bool:
        return self._mode() in {"paper", "paper_trade", "paper_trading"}

    def _is_live(self) -> bool:
        return self._mode() in {"live", "automated", "auto"}

    @staticmethod
    def _alpaca_ready(client) -> bool:
        return bool(client and getattr(client, "api_key", "") and getattr(client, "secret_key", ""))

    @staticmethod
    def _tradier_ready(client) -> bool:
        return bool(client and getattr(client, "token", "") and getattr(client, "account_id", ""))

    def get_alpaca_client(self, order: bool = True):
        """Return the Alpaca client selected by Telegram mode.

        For order=True, alerts_only intentionally returns None and paper never falls back
        to live credentials. That prevents accidental live orders while the UI says Paper.
        """
        if self._is_alerts_only():
            if order:
                return None
            return self.alpaca_paper_client if self._alpaca_ready(self.alpaca_paper_client) else self.alpaca_live_client
        if self._is_paper():
            return self.alpaca_paper_client if self._alpaca_ready(self.alpaca_paper_client) else None
        if self._is_live():
            return self.alpaca_live_client if self._alpaca_ready(self.alpaca_live_client) else self.alpaca_client
        return None

    def get_tradier_client(self, order: bool = True):
        """Return the Tradier client selected by Telegram mode.

        For order=True, alerts_only intentionally returns None and paper never falls back
        to production credentials. That prevents accidental live options orders.
        For account reads, the current mode is respected so Paper shows paper positions.
        """
        if self._is_alerts_only():
            if order:
                return None
            return self.tradier_paper_client if self._tradier_ready(self.tradier_paper_client) else self.tradier_live_client
        if self._is_paper():
            return self.tradier_paper_client if self._tradier_ready(self.tradier_paper_client) else None
        if self._is_live():
            return self.tradier_live_client if self._tradier_ready(self.tradier_live_client) else self.tradier_client
        return None

    def get_tradier_market_data_client(self):
        """Return the best Tradier client for option-chain market data.

        Chain/expiration reads are market data, not order execution. Prefer the live
        Tradier client because the sandbox frequently returns empty chains even when
        orders should still route to Paper in Paper mode.
        """
        if self._tradier_ready(self.tradier_live_client):
            return self.tradier_live_client
        if self._tradier_ready(self.tradier_client):
            return self.tradier_client
        if self._tradier_ready(self.tradier_paper_client):
            return self.tradier_paper_client
        return None

    async def get_expirations(self, symbol: str) -> list[str]:
        client = self.get_tradier_market_data_client()
        if client is None:
            return []
        return await client.get_expirations(symbol)

    async def get_options_chain(self, symbol: str, expiration: str | None = None, greeks: bool = True):
        client = self.get_tradier_market_data_client()
        if client is None:
            return []
        return await client.get_options_chain(symbol=symbol, expiration=expiration, greeks=greeks)

    async def place_order(self, order_request):
        """Compatibility adapter for older alert-service OrderRequest objects."""
        trade = {
            "symbol": getattr(order_request, "symbol", None),
            "side": getattr(order_request, "side", "buy"),
            "type": getattr(order_request, "instrument_type", "stock"),
            "instrument_type": getattr(order_request, "instrument_type", "stock"),
            "qty": getattr(order_request, "quantity", 1),
            "quantity": getattr(order_request, "quantity", 1),
            "order_type": getattr(order_request, "order_type", "market"),
            "limit_price": getattr(order_request, "limit_price", None),
            "stop_price": getattr(order_request, "stop_price", None),
        }
        option_symbol = getattr(order_request, "option_symbol", None)
        if option_symbol:
            trade["option_symbol"] = option_symbol
        return await self.execute(trade)

    async def execute(self, trade: Dict[str, Any]):
        trade_type = str(trade.get("type") or trade.get("instrument_type") or "stock").lower()
        if self._is_alerts_only():
            return {"status": "blocked", "reason": "execution mode is alerts_only", "trade": trade}
        if trade_type in {"option", "options"} and trade.get("legs"):
            return await self._execute_multileg_option(trade)
        if trade_type in {"option", "options"}:
            return await self._execute_option(trade)
        return await self._execute_stock(trade)

    async def _execute_stock(self, trade: Dict[str, Any]):
        client = self.get_alpaca_client(order=True)
        if client is None:
            return {
                "status": "blocked",
                "reason": f"Alpaca client for mode '{self._mode()}' is not configured",
                "trade": trade,
            }

        symbol = trade["symbol"]
        qty = trade.get("qty", 1)
        side = trade.get("side", "buy")
        limit_price = trade.get("limit_price")
        order_type = trade.get("order_type") or ("limit" if limit_price not in (None, "") else "market")

        if hasattr(client, "place_order"):
            return await client.place_order(
                symbol=symbol,
                qty=qty,
                side=side,
                order_type=order_type,
                limit_price=limit_price,
            )

        if hasattr(client, "submit_order"):
            kwargs = {"symbol": symbol, "qty": qty, "side": side, "type": order_type, "time_in_force": "day"}
            if limit_price:
                kwargs["limit_price"] = limit_price
            return await client.submit_order(**kwargs)

        raise RuntimeError("Alpaca client does not expose a supported order method")

    async def _execute_option(self, trade: Dict[str, Any]):
        client = self.get_tradier_client(order=True)
        if client is None:
            return {
                "status": "blocked",
                "reason": f"Tradier client for mode '{self._mode()}' is not configured",
                "trade": trade,
            }

        symbol = trade["symbol"]
        qty = trade.get("qty", 1)
        side = trade.get("side", "buy_to_open")
        option_symbol = trade.get("option_symbol")
        if not option_symbol:
            raise RuntimeError("Option trade missing option_symbol")

        return await client.place_option_order(
            symbol=symbol,
            qty=qty,
            side=side,
            option_symbol=option_symbol,
            order_type=trade.get("order_type", "market"),
            price=trade.get("limit_price") or trade.get("price"),
            stop=trade.get("stop") or trade.get("stop_price"),
        )

    async def _execute_multileg_option(self, trade: Dict[str, Any]):
        client = self.get_tradier_client(order=True)
        if client is None:
            return {
                "status": "blocked",
                "reason": f"Tradier client for mode '{self._mode()}' is not configured",
                "trade": trade,
            }

        symbol = trade["symbol"]
        legs = list(trade.get("legs", []))
        quantity = int(trade.get("qty", trade.get("quantity", 1)) or 1)
        if not legs:
            raise RuntimeError("Multi-leg option trade missing legs")

        return await client.place_multileg_order(
            symbol=symbol,
            legs=legs,
            quantity=quantity,
            order_type=trade.get("order_type", "market"),
            price=trade.get("limit_price") or trade.get("price"),
        )
