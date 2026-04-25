from __future__ import annotations

from datetime import datetime
from typing import Any

from execution.ladder_manager import LadderManager
from services.options_order_service import OptionsOrderService


class LiveExecutionService:
    def __init__(self, settings_repo, execution_router, trailing_stop_service=None, risk_service=None):
        self.settings_repo = settings_repo
        self.execution_router = execution_router
        self.trailing_stop_service = trailing_stop_service
        self.risk_service = risk_service
        self.ladder_manager = LadderManager()
        self.options_order_service = OptionsOrderService()

    def _infer_trade_style(self, trade_style: str | None = None, strategy: str | None = None) -> str:
        if trade_style:
            return self.settings_repo.normalize_execution_scope(trade_style)
        text = str(strategy or "").strip().lower()
        if "swing" in text or "overnight" in text:
            return "swing_trade"
        return "day_trade"

    def _get_execution_profile(self, trade_style: str | None = None, strategy: str | None = None) -> dict[str, Any]:
        scope = self._infer_trade_style(trade_style, strategy)
        if hasattr(self.settings_repo, "get_execution_settings"):
            profile = self.settings_repo.get_execution_settings(scope)
        else:
            profile = self.settings_repo.get("execution_settings", {}) or {}
        profile = dict(profile)
        profile["trade_style"] = scope
        return profile

    def _entry_cutoff_allows_new_positions(self, profile: dict[str, Any], now: datetime | None = None) -> tuple[bool, str | None]:
        cutoff = str(profile.get("time_of_day_restrictor") or "").strip()
        if not cutoff:
            return True, None
        try:
            hour, minute = [int(part) for part in cutoff.split(":", 1)]
        except Exception:
            return True, None
        now = now or datetime.now()
        current_minutes = now.hour * 60 + now.minute
        cutoff_minutes = hour * 60 + minute
        if current_minutes > cutoff_minutes:
            return False, f"entry cutoff reached ({cutoff})"
        return True, None

    def can_open_new_position(self, open_positions_count: int, trade_style: str | None = None, strategy: str | None = None) -> tuple[bool, str | None]:
        profile = self._get_execution_profile(trade_style, strategy)
        allowed, reason = self._entry_cutoff_allows_new_positions(profile)
        if not allowed:
            return False, reason
        max_positions = int(profile.get("max_concurrent_positions", 0) or 0)
        if max_positions > 0 and int(open_positions_count) >= max_positions:
            return False, f"max concurrent positions reached ({max_positions})"
        if self.risk_service is not None and hasattr(self.risk_service, "can_open_new_position"):
            risk_allowed, risk_reason = self.risk_service.can_open_new_position(
                trade_style=profile.get("trade_style"),
                strategy=strategy,
            )
            if not risk_allowed:
                return False, risk_reason
        return True, None

    async def submit_stock_ladder(
        self,
        symbol: str,
        side: str,
        total_size: int,
        entry_price: float,
        mode: str,
        strategy: str,
        trade_style: str | None = None,
        open_positions_count: int = 0,
    ) -> dict[str, Any]:
        profile = self._get_execution_profile(trade_style, strategy)
        allowed, reason = self.can_open_new_position(open_positions_count, trade_style=profile["trade_style"], strategy=strategy)
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
            "mode": mode,
            "strategy": strategy,
            "trade_style": profile["trade_style"],
            "profile": profile,
            "entries": entries,
            "submit_ready": str(mode).lower() != "alerts_only" and allowed,
            "blocked_reason": reason,
        }

    async def build_exit_ladder(
        self,
        symbol: str,
        side: str,
        total_size: int,
        entry_price: float,
        stop_loss: float | None,
        mode: str,
        strategy: str,
        rr_targets: list[float] | None = None,
        trade_style: str | None = None,
    ) -> dict[str, Any]:
        profile = self._get_execution_profile(trade_style, strategy)
        stop_loss_pct = float(profile.get("stop_loss_pct", 0.08) or 0.08)
        effective_stop = float(stop_loss) if stop_loss is not None else (
            entry_price * (1 - stop_loss_pct) if str(side).upper() == "LONG" else entry_price * (1 + stop_loss_pct)
        )
        take_profit_pct = float(profile.get("take_profit_pct", 0.20) or 0.20)
        if rr_targets is None:
            rr_targets = [1.0, 1.5, 2.0]
            if take_profit_pct > 0 and effective_stop != entry_price:
                risk_per_unit = abs(float(entry_price) - float(effective_stop))
                rr_targets.append(round((entry_price * take_profit_pct) / risk_per_unit, 2))
        risk_per_unit = abs(float(entry_price) - float(effective_stop))
        exits = self.ladder_manager.build_exit_ladder(
            entry_price=entry_price,
            side=side,
            total_size=total_size,
            rr_targets=sorted(set(rr_targets)),
            risk_per_unit=risk_per_unit,
        )
        return {
            "symbol": symbol,
            "side": side,
            "mode": mode,
            "strategy": strategy,
            "trade_style": profile["trade_style"],
            "profile": profile,
            "stop_loss": round(effective_stop, 4),
            "risk_per_unit": risk_per_unit,
            "exits": exits,
            "submit_ready": str(mode).lower() != "alerts_only",
        }

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
        payload.update({
            "symbol": symbol,
            "type": "option",
            "qty": quantity,
            "order_type": order_type,
        })
        if price is not None:
            payload["limit_price"] = float(price)
        if self.risk_service is not None and hasattr(self.risk_service, "can_open_new_position"):
            allowed, reason = self.risk_service.can_open_new_position(trade_style="options", strategy="options")
            if not allowed:
                return {"status": "blocked", "reason": reason, "symbol": symbol, "option_symbol": option_symbol}
        result = await self.execution_router.execute(payload)
        return result

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
        order.update({
            "symbol": symbol,
            "type": "option",
            "qty": quantity,
            "order_type": order_type,
        })
        if price is not None:
            order["limit_price"] = float(price)
        if self.risk_service is not None and hasattr(self.risk_service, "can_open_new_position"):
            allowed, reason = self.risk_service.can_open_new_position(trade_style="options", strategy="options")
            if not allowed:
                return {"status": "blocked", "reason": reason, "symbol": symbol, "legs": [long_symbol, short_symbol]}
        result = await self.execution_router.execute(order)
        return result
