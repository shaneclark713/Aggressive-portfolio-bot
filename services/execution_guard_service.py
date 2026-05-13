from __future__ import annotations

import hashlib
import json
import logging
import time
from contextlib import contextmanager
from typing import Any, Iterator

logger = logging.getLogger("aggressive_portfolio_bot.services.execution_guard")


class ExecutionGuardService:
    """In-process execution safety guard.

    This prevents duplicate submissions caused by Telegram double taps, retry loops,
    scheduler overlap, or short Render hiccups. It is intentionally conservative and
    analysis-only until explicitly called by execution services.
    """

    def __init__(self, execution_log_repo=None, default_cooldown_seconds: int = 45):
        self.execution_log_repo = execution_log_repo
        self.default_cooldown_seconds = int(default_cooldown_seconds)
        self._active_locks: set[str] = set()
        self._recent_keys: dict[str, float] = {}
        self._last_status: dict[str, Any] = {
            "blocked": 0,
            "allowed": 0,
            "last_block_reason": None,
            "last_key": None,
        }

    def build_key(self, payload: dict[str, Any], namespace: str = "order") -> str:
        stable_payload = {
            "namespace": namespace,
            "symbol": str(payload.get("symbol") or payload.get("underlying") or "").upper(),
            "option_symbol": payload.get("option_symbol") or payload.get("symbol_option"),
            "side": str(payload.get("side") or payload.get("action") or "").lower(),
            "type": str(payload.get("type") or payload.get("instrument_type") or "").lower(),
            "qty": payload.get("qty") or payload.get("quantity"),
            "order_type": str(payload.get("order_type") or payload.get("type") or "").lower(),
            "limit_price": payload.get("limit_price") or payload.get("price"),
            "strategy": payload.get("strategy"),
        }
        raw = json.dumps(stable_payload, sort_keys=True, default=str)
        digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
        return f"{namespace}:{stable_payload['symbol']}:{digest}"

    def check(self, key: str, cooldown_seconds: int | None = None) -> tuple[bool, str | None]:
        now = time.time()
        cooldown = self.default_cooldown_seconds if cooldown_seconds is None else int(cooldown_seconds)
        self._purge_expired(now, max(cooldown, self.default_cooldown_seconds))
        if key in self._active_locks:
            return False, f"execution lock already active for {key}"
        last_seen = self._recent_keys.get(key)
        if last_seen is not None and now - last_seen < cooldown:
            remaining = round(cooldown - (now - last_seen), 1)
            return False, f"duplicate execution cooldown active for {key} ({remaining}s remaining)"
        return True, None

    @contextmanager
    def guarded(self, key: str, payload: dict[str, Any] | None = None, cooldown_seconds: int | None = None) -> Iterator[tuple[bool, str | None]]:
        allowed, reason = self.check(key, cooldown_seconds=cooldown_seconds)
        if not allowed:
            self._last_status.update({"blocked": self._last_status["blocked"] + 1, "last_block_reason": reason, "last_key": key})
            self._log("execution_guard_blocked", {"key": key, "reason": reason, "payload": payload or {}})
            yield False, reason
            return
        self._active_locks.add(key)
        self._recent_keys[key] = time.time()
        self._last_status.update({"allowed": self._last_status["allowed"] + 1, "last_key": key})
        self._log("execution_guard_allowed", {"key": key, "payload": payload or {}})
        try:
            yield True, None
        finally:
            self._active_locks.discard(key)

    def mark_failure(self, key: str, error: str, release_cooldown: bool = False) -> None:
        if release_cooldown:
            self._recent_keys.pop(key, None)
        self._log("execution_guard_failure", {"key": key, "error": error, "release_cooldown": release_cooldown})

    def status(self) -> dict[str, Any]:
        return {
            **self._last_status,
            "active_locks": sorted(self._active_locks),
            "recent_key_count": len(self._recent_keys),
            "default_cooldown_seconds": self.default_cooldown_seconds,
        }

    def _purge_expired(self, now: float, ttl: int) -> None:
        expired = [key for key, ts in self._recent_keys.items() if now - ts > ttl]
        for key in expired:
            self._recent_keys.pop(key, None)

    def _log(self, event_type: str, payload: dict[str, Any]) -> None:
        if self.execution_log_repo is None:
            return
        try:
            self.execution_log_repo.log_event(event_type, payload)
        except Exception as exc:
            logger.warning("Failed to write execution guard audit event: %s", exc)
