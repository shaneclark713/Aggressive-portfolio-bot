from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("aggressive_portfolio_bot.services.spy_scan_journal")


class SpyScanJournalService:
    """Thin wrapper that records SPY/XSP desk scan payloads without changing analysis logic."""

    def __init__(self, delegate, journal_repo):
        self.delegate = delegate
        self.journal_repo = journal_repo

    def __getattr__(self, name: str):
        return getattr(self.delegate, name)

    def _record(self, scan_type: str, payload: dict[str, Any]) -> None:
        if self.journal_repo is None:
            return
        try:
            self.journal_repo.record_scan(scan_type, payload)
        except Exception as exc:
            logger.warning("Failed to journal SPY/XSP scan type=%s: %s", scan_type, exc)

    async def analyze(self, scan_type: str = "manual") -> dict[str, Any]:
        payload = await self.delegate.analyze()
        self._record(scan_type, payload)
        return payload

    async def run_breakdown(self) -> dict[str, Any]:
        payload = await self.delegate.analyze()
        self._record("breakdown", payload)
        await self.delegate.telegram_app.bot.send_message(
            chat_id=self.delegate.chat_id,
            text=self.delegate.format_report(payload, "🧭 6:15 AM SPY/XSP 0DTE Direction Desk"),
            parse_mode="HTML",
        )
        return payload

    async def run_midday(self) -> dict[str, Any]:
        payload = await self.delegate.analyze()
        self._record("midday", payload)
        await self.delegate.telegram_app.bot.send_message(
            chat_id=self.delegate.chat_id,
            text=self.delegate.format_report(payload, "☀️ 10:00 AM ET SPY/XSP 0DTE Midday Desk"),
            parse_mode="HTML",
        )
        return payload
