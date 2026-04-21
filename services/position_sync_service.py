from __future__ import annotations


class PositionSyncService:
    def __init__(self, trailing_stop_service, alpaca_client=None, tradier_client=None):
        self.trailing_stop_service = trailing_stop_service
        self.alpaca_client = alpaca_client
        self.tradier_client = tradier_client

    async def sync_stock_position(self, position_id: str, symbol: str, entry_price: float, current_price: float, stop_loss: float, side: str = "LONG") -> dict:
        existing = self.trailing_stop_service.get_position(position_id)
        if existing is None:
            state = self.trailing_stop_service.create_position(position_id=position_id, entry_price=entry_price, stop_loss=stop_loss, side=side)
        else:
            state = existing
        updated = self.trailing_stop_service.update_position(position_id, current_price) or state
        updated["symbol"] = symbol
        updated["position_id"] = position_id
        return updated

    async def sync_demo_positions(self) -> dict:
        return {
            "SPY-demo": await self.sync_stock_position("SPY-demo", "SPY", 510.0, 514.5, 505.0, "LONG"),
            "QQQ-demo": await self.sync_stock_position("QQQ-demo", "QQQ", 430.0, 426.0, 435.0, "SHORT"),
        }
