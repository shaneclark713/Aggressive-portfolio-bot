from __future__ import annotations

import json
from typing import Any

from execution.ladder_manager import LadderManager
from execution.strategy_execution_profiles import StrategyExecutionProfiles
from services.options_order_service import OptionsOrderService


DEFAULT_UI_EXECUTION = {
    "risk_pct": 0.01,
    "atr_multiplier": 1.0,
    "position_mode": "auto",
    "take_profit": 0.05,
    "stop_loss": 0.02,
    "max_spread_pct": 0.03,
    "min_volume": 500000,
    "max_slippage_pct": 0.02,
    "max_concurrent_positions": 3,
    "entry_cutoff_time": "15:00",
    "ladder_steps": 3,
    "ladder_spacing_pct": 0.01,
    "trail_type": "percent",
    "trail_value": 0.02,
}


class LiveExecutionService:
    def __init__(self, settings_repo, execution_router, trailing_stop_service=None):
        self.settings_repo = settings_repo
        self.execution_router = execution_router
        self.trailing_stop_service = trailing_stop_service
        self.ladder_manager = LadderManager()
        self.profile_store = StrategyExecutionProfiles(settings_repo)
        self.options_order_service = OptionsOrderService()

    def _normalize_trade_style(self, trade_style: str | None) -> str:
        value = str(trade_style or "day_trade").lower().strip()
        return value if value in {"day_trade", "swing_trade"} else "day_trade"

    def _parse_meta(self, value: Any) -> dict[str, Any]:
        if value is None:
            return {}
        if isinstance(value, dict):
            return value
        if isinstance(value, str):
            try:
                return json.loads(value)
            except Exception:
                return {}
        return {}

    def get_ui_execution_settings(self, trade_style: str | None = None) -> dict[str, Any]:
        style = self._normalize_trade_style(trade_style)
        overrides = {}
        if hasattr(self.settings_repo, "get_filter_overrides"):
            try:
                overrides = self.settings_repo.get_filter_overrides() or {}
            except Exception:
                overrides = {}
        blob = self._parse_meta(overrides.get("__meta__.ui.execution_settings"))
        if "profiles" in blob:
            profiles = blob.get("profiles") or {}
            return {**DEFAULT_UI_EXECUTION, **dict(profiles.get(style) or {})}
        legacy = {k: v for k, v in blob.items() if k in DEFAULT_UI_EXECUTION}
        return {**DEFAULT_UI_EXECUTION, **legacy}

    async def submit_stock_ladder(
        self,
        symbol: str,
        side: str,
        total_size: int,
        entry_price: float,
        mode: str,
        strategy: str,
        trade_style: str | None = None,
    ) -> dict[str, Any]:
        normalized_mode = self.profile_store.normalize_mode(mode)
        normalized_strategy = self.profile_store.normalize_strategy(strategy)
        profile = self.profile_store.get_profile(normalized_mode, normalized_strategy)
        ui_settings = self.get_ui_execution_settings(trade_style)
        entries = self.ladder_manager.build_entry_ladder(
            entry_price=entry_price,
            side=side,
            total_size=total_size,
            steps=int(profile.get("ladder_steps", ui_settings.get("ladder_steps", 3))),
            spacing_pct=float(profile.get("ladder_spacing_pct", ui_settings.get("ladder_spacing_pct", 0.01))),
        )
        return {
            "symbol": symbol,
            "side": side,
            "mode": normalized_mode,
            "strategy": normalized_strategy,
            "execution_profile": self._normalize_trade_style(trade_style),
            "execution_settings": ui_settings,
            "profile": profile,
            "entries": entries,
            "submit_ready": normalized_mode != "alerts_only",
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
        trade_style: str | None = None,
    ) -> dict[str, Any]:
        normalized_mode = self.profile_store.normalize_mode(mode)
        normalized_strategy = self.profile_store.normalize_strategy(strategy)
        profile = self.profile_store.get_profile(normalized_mode, normalized_strategy)
        ui_settings = self.get_ui_execution_settings(trade_style)
        rr_targets = rr_targets or [1.0, 1.5, 2.0]
        risk_per_unit = abs(float(entry_price) - float(stop_loss))
        exits = self.ladder_manager.build_exit_ladder(
            entry_price=entry_price,
            side=side,
            total_size=total_size,
            rr_targets=rr_targets,
            risk_per_unit=risk_per_unit,
        )
        return {
            "symbol": symbol,
            "side": side,
            "mode": normalized_mode,
            "strategy": normalized_strategy,
            "execution_profile": self._normalize_trade_style(trade_style),
            "execution_settings": ui_settings,
            "profile": profile,
            "risk_per_unit": risk_per_unit,
            "exits": exits,
            "submit_ready": normalized_mode != "alerts_only",
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
        trade_style: str | None = None,
    ) -> dict[str, Any]:
        return await self.build_exit_ladder(symbol, side, total_size, entry_price, stop_loss, mode, strategy, rr_targets=rr_targets, trade_style=trade_style)

    async def submit_single_option(
        self,
        symbol: str,
        option_symbol: str,
        side: str,
        quantity: int,
        order_type: str = "market",
        price: float | None = None,
    ) -> Any:
        payload = self.options_order_service.build_single_leg_order(option_symbol, side, quantity)
        payload["symbol"] = symbol
        payload["type"] = "option"
        payload["qty"] = quantity
        payload["order_type"] = order_type
        if price is not None:
            payload["price"] = float(price)
            payload["limit_price"] = float(price)
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
    ) -> Any:
        order = self.options_order_service.build_vertical_spread_order(long_symbol, short_symbol, quantity, debit=debit)
        order["symbol"] = symbol
        order["type"] = "option"
        order["qty"] = quantity
        order["order_type"] = order_type
        if price is not None:
            order["price"] = float(price)
            order["limit_price"] = float(price)
        return await self.execution_router.execute(order)

    async def execute_triggered_trailing_exits(self, limit_buffer_pct: float = 0.0) -> dict[str, Any]:
        if self.trailing_stop_service is None:
            return {"triggered": 0, "results": []}

        if hasattr(self.trailing_stop_service, "evaluate_triggers"):
            triggered = self.trailing_stop_service.evaluate_triggers() or {}
        elif hasattr(self.trailing_stop_service, "list_positions"):
            triggered = {
                position_id: row
                for position_id, row in (self.trailing_stop_service.list_positions() or {}).items()
                if isinstance(row, dict) and row.get("stop_hit")
            }
        else:
            triggered = {}

        results: list[dict[str, Any]] = []
        for position_id, row in triggered.items():
            state = dict(row or {})
            metadata = dict(state.get("metadata") or {})
            if metadata.get("exit_submitted"):
                continue

            asset_type = str(state.get("asset_type", "stock")).lower()
            side = str(state.get("side", "LONG")).upper()
            quantity = abs(float(state.get("quantity", 0) or 0))
            if quantity <= 0:
                quantity = 1

            if asset_type in {"option", "options"}:
                close_side = "sell_to_close" if side in {"LONG", "BUY"} else "buy_to_close"
                payload = {
                    "type": "option",
                    "symbol": metadata.get("underlying") or state.get("symbol"),
                    "option_symbol": metadata.get("option_symbol") or state.get("symbol"),
                    "side": close_side,
                    "qty": int(quantity),
                }
            else:
                close_side = "sell" if side in {"LONG", "BUY"} else "buy"
                payload = {
                    "type": "stock",
                    "symbol": state.get("symbol"),
                    "side": close_side,
                    "qty": int(quantity),
                }
                stop_price = float(state.get("active_stop", 0) or 0)
                if stop_price > 0 and limit_buffer_pct:
                    if close_side == "sell":
                        payload["limit_price"] = round(stop_price * (1 - float(limit_buffer_pct)), 4)
                    else:
                        payload["limit_price"] = round(stop_price * (1 + float(limit_buffer_pct)), 4)

            try:
                result = await self.execution_router.execute(payload)
                metadata["exit_submitted"] = True
                state["metadata"] = metadata
                results.append({"position_id": position_id, "payload": payload, "result": result})
            except Exception as exc:
                results.append({"position_id": position_id, "payload": payload, "error": str(exc)})

        return {"triggered": len(results), "results": results}
