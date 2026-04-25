from __future__ import annotations

from typing import Any


class RiskService:
    """Runtime risk guard for broker execution.

    The max consecutive losses guard is intentionally enforced before new entries
    are submitted. A value of 0 disables the guard.
    """

    def __init__(self, settings_repo, trade_repo=None, config_service=None):
        self.settings_repo = settings_repo
        self.trade_repo = trade_repo
        self.config_service = config_service

    def _normalize_scope(self, trade_style: str | None = None, strategy: str | None = None) -> str:
        if hasattr(self.settings_repo, "normalize_execution_scope"):
            if trade_style:
                return self.settings_repo.normalize_execution_scope(trade_style)
            text = str(strategy or "").strip().lower()
            if "option" in text:
                return self.settings_repo.normalize_execution_scope("options")
            if "swing" in text or "overnight" in text:
                return self.settings_repo.normalize_execution_scope("swing_trade")
            return self.settings_repo.normalize_execution_scope("day_trade")
        return trade_style or "day_trade"

    def get_consecutive_loss_count(self) -> int:
        if self.trade_repo is None:
            return 0
        if hasattr(self.trade_repo, "get_consecutive_loss_count"):
            return int(self.trade_repo.get_consecutive_loss_count() or 0)
        if not hasattr(self.trade_repo, "get_recent_closed_trades"):
            return 0
        count = 0
        for trade in self.trade_repo.get_recent_closed_trades(limit=50):
            try:
                pnl = float(trade.get("pnl", 0) or 0)
            except Exception:
                pnl = 0.0
            if pnl < 0:
                count += 1
            else:
                break
        return count

    def get_max_consecutive_losses(self, trade_style: str | None = None, strategy: str | None = None) -> int:
        scope = self._normalize_scope(trade_style, strategy)
        if hasattr(self.settings_repo, "get_execution_settings"):
            profile: dict[str, Any] = self.settings_repo.get_execution_settings(scope) or {}
        else:
            profile = self.settings_repo.get("execution_settings", {}) or {}
        return int(profile.get("max_consecutive_losses", 0) or 0)

    def consecutive_loss_guard(self, trade_style: str | None = None, strategy: str | None = None) -> tuple[bool, str | None]:
        max_losses = self.get_max_consecutive_losses(trade_style, strategy)
        if max_losses <= 0:
            return True, None
        current_losses = self.get_consecutive_loss_count()
        if current_losses >= max_losses:
            return False, f"max consecutive losses reached ({current_losses}/{max_losses})"
        return True, None

    def can_open_new_position(self, trade_style: str | None = None, strategy: str | None = None) -> tuple[bool, str | None]:
        return self.consecutive_loss_guard(trade_style=trade_style, strategy=strategy)
