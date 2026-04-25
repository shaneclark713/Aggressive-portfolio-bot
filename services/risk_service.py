from __future__ import annotations

from datetime import datetime, time
from typing import Any
from zoneinfo import ZoneInfo


class RiskService:
    """Runtime risk guard for broker execution.

    Enforced before new entries are submitted. Current guards:
    - max consecutive closed-trade losses
    - market-session gate for stock/options entries
    """

    DEFAULT_TZ = "America/New_York"

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

    def _profile(self, trade_style: str | None = None, strategy: str | None = None) -> dict[str, Any]:
        scope = self._normalize_scope(trade_style, strategy)
        if hasattr(self.settings_repo, "get_execution_settings"):
            profile = self.settings_repo.get_execution_settings(scope) or {}
        else:
            profile = self.settings_repo.get("execution_settings", {}) or {}
        return dict(profile)

    @staticmethod
    def _to_bool(value: Any, default: bool = False) -> bool:
        if isinstance(value, bool):
            return value
        if value is None:
            return default
        return str(value).strip().lower() in {"1", "true", "yes", "on", "enabled"}

    @staticmethod
    def _parse_hhmm(value: Any, default: str) -> time:
        text = str(value or default).strip() or default
        try:
            hour, minute = [int(part) for part in text.split(":", 1)]
            return time(hour=max(0, min(23, hour)), minute=max(0, min(59, minute)))
        except Exception:
            hour, minute = [int(part) for part in default.split(":", 1)]
            return time(hour=hour, minute=minute)

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
        profile = self._profile(trade_style, strategy)
        return int(profile.get("max_consecutive_losses", 0) or 0)

    def consecutive_loss_guard(self, trade_style: str | None = None, strategy: str | None = None) -> tuple[bool, str | None]:
        max_losses = self.get_max_consecutive_losses(trade_style, strategy)
        if max_losses <= 0:
            return True, None
        current_losses = self.get_consecutive_loss_count()
        if current_losses >= max_losses:
            return False, f"max consecutive losses reached ({current_losses}/{max_losses})"
        return True, None

    def market_session_guard(
        self,
        trade_style: str | None = None,
        strategy: str | None = None,
        now: datetime | None = None,
    ) -> tuple[bool, str | None]:
        profile = self._profile(trade_style, strategy)
        if not self._to_bool(profile.get("market_hours_only", True), True):
            return True, None

        timezone_name = str(profile.get("market_timezone") or self.DEFAULT_TZ)
        try:
            tz = ZoneInfo(timezone_name)
        except Exception:
            tz = ZoneInfo(self.DEFAULT_TZ)

        current_dt = now.astimezone(tz) if now is not None and now.tzinfo else now or datetime.now(tz)
        if current_dt.tzinfo is None:
            current_dt = current_dt.replace(tzinfo=tz)

        if current_dt.weekday() >= 5:
            return False, "market is closed: weekend"

        current = current_dt.time().replace(second=0, microsecond=0)
        premarket_start = self._parse_hhmm(profile.get("premarket_start_time"), "04:00")
        regular_open = self._parse_hhmm(profile.get("regular_market_open_time"), "09:30")
        regular_close = self._parse_hhmm(profile.get("regular_market_close_time"), "16:00")
        afterhours_end = self._parse_hhmm(profile.get("afterhours_end_time"), "20:00")
        allow_premarket = self._to_bool(profile.get("allow_premarket_entries", False), False)
        allow_afterhours = self._to_bool(profile.get("allow_afterhours_entries", False), False)

        if regular_open <= current <= regular_close:
            return True, None
        if allow_premarket and premarket_start <= current < regular_open:
            return True, None
        if allow_afterhours and regular_close < current <= afterhours_end:
            return True, None

        return False, (
            "market is closed for new entries "
            f"({current_dt.strftime('%a %H:%M %Z')}; regular {regular_open.strftime('%H:%M')}-{regular_close.strftime('%H:%M')})"
        )

    def can_open_new_position(self, trade_style: str | None = None, strategy: str | None = None) -> tuple[bool, str | None]:
        allowed, reason = self.consecutive_loss_guard(trade_style=trade_style, strategy=strategy)
        if not allowed:
            return False, reason
        return self.market_session_guard(trade_style=trade_style, strategy=strategy)
