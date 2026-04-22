from __future__ import annotations

from typing import Any

from execution.ladder_manager import LadderManager
from execution.strategy_execution_profiles import StrategyExecutionProfiles
from services.options_order_service import OptionsOrderService


class LiveExecutionService:
    def __init__(self, settings_repo, execution_router, trailing_stop_service=None):
        self.settings_repo = settings_repo
        self.execution_router = execution_router
        self.trailing_stop_service = trailing_stop_service
        self.ladder_manager = LadderManager()
        self.profile_store = StrategyExecutionProfiles(settings_repo)
        self.options_order_service = OptionsOrderService()

    async def submit_stock_ladder(
        self,
        symbol: str,
        side: str,
        total_size: int,
        entry_price: float,
        mode: str,
        strategy: str,
    ) -> dict[str, Any]:
        profile = self.profile_store.get_profile(mode, strategy)
        entries = self.ladder_manager.build_entry_ladder(
            entry_price=entry_price,
            side=side,
            total_size=total_size,
            steps=int(profile.get("ladder_steps", 3)),
            spacing_pct=float(profile.get("ladder_spacing_pct", 0.01)),
        )
        return {
            "symbol": symbol,
            "side": side,
            "mode": self.profile_store.normalize_mode(mode),
            "strategy": self.profile_store.normalize_strategy(strategy),
            "profile": profile,
            "entries": entries,
            "submit_ready": self.profile_store.normalize_mode(mode) != "alerts_only",
        }

    async def submit_exit_ladder(
        self,
        symbol: str,
        side: str,
        total_size: int,
        entry_price: float,
        stop_loss: float,
        mode: str,
        strategy: str,
        rr_targets: list[float] | None = None,
    ) -> dict[str, Any]:
        profile = self.profile_store.get_profile(mode, strategy)
        rr_targets = rr_targets or profile.get("rr_targets") or [1.0, 1.5, 2.0]
        risk_per_unit = abs(float(entry_price) - float(stop_loss))
        exits = self.ladder_manager.build_exit_ladder(
            entry_price=entry_price,
            side=side,
            total_size=total_size,
            rr_targets=[float(item) for item in rr_targets],
            risk_per_unit=risk_per_unit,
        )
        return {
            "symbol": symbol,
            "side": side,
            "mode": self.profile_store.normalize_mode(mode),
            "strategy": self.profile_store.normalize_strategy(strategy),
            "profile": profile,
            "risk_per_unit": risk_per_unit,
            "exits": exits,
            "submit_ready": self.profile_store.normalize_mode(mode) != "alerts_only",
        }

    async def build_exit_ladder(
        self,
        symbol: str,
        side: str,
        total_size: int,
        entry_price: float,
        stop_loss: float,
        mode: str,
        strategy: str,
        rr_targets: list[float] | None = None,
    ) -> dict[str, Any]:
        return await self.submit_exit_ladder(symbol, side, total_size, entry_price, stop_loss, mode, strategy, rr_targets=rr_targets)

    async def submit_single_option(
        self,
        symbol: str,
        option_symbol: str,
        side: str,
        quantity: int,
        order_type: str = "market",
        price: float | None = None,
        duration: str = "day",
    ) -> Any:
        payload = self.options_order_service.build_single_leg_order(option_symbol, side, quantity, order_type=order_type, price=price, duration=duration)
        payload["symbol"] = symbol
        payload["type"] = "option"
        payload["qty"] = quantity
        return await self.execution_router.execute(payload)

    async def submit_vertical_spread(
        self,
        symbol: str,
        long_symbol: str,
        short_symbol: str,
        quantity: int,
        debit: bool = True,
        order_type: str = "market",
        price: float | None = None,
        duration: str = "day",
    ) -> Any:
        order = self.options_order_service.build_vertical_spread_order(long_symbol, short_symbol, quantity, debit=debit, order_type=order_type, price=price, duration=duration)
        order["symbol"] = symbol
        order["type"] = "option"
        order["qty"] = quantity
        return await self.execution_router.execute(order)

    async def execute_triggered_trailing_exits(self, limit_buffer_pct: float = 0.0) -> dict[str, Any]:
        if self.trailing_stop_service is None:
            raise RuntimeError("Trailing stop service not configured")
        payloads = self.trailing_stop_service.build_exit_payloads(limit_buffer_pct=limit_buffer_pct)
        results: list[dict[str, Any]] = []
        for payload in payloads:
            position_id = str(payload.pop("position_id"))
            try:
                result = await self.execution_router.execute(payload)
                self.trailing_stop_service.mark_exit_pending(position_id, result=result)
                results.append({"position_id": position_id, "payload": payload, "result": result})
            except Exception as exc:
                results.append({"position_id": position_id, "payload": payload, "error": str(exc)})
        return {"triggered": len(payloads), "results": results}
