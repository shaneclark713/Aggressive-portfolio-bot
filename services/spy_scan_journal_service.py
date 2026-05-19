from __future__ import annotations

import logging
from typing import Any
from database.ecosystem_state_repository import record_ecosystem_state

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
        try:
            record_ecosystem_state(self.journal_repo.conn,payload,source=f"spy_0dte:{scan_type}")
        except Exception as exc:
            logger.warning("Failed ecosystem persistence type=%s: %s", scan_type, exc)

    async def analyze(self, scan_type: str = "manual") -> dict[str, Any]:
        payload = await self.delegate.analyze()
        self._record(scan_type, payload)
        return payload

    async def run_breakdown(self) -> dict[str, Any]:
        payload = await self.delegate.analyze()
        self._record("breakdown", payload)
        return payload

    async def run_midday(self) -> dict[str, Any]:
        payload = await self.delegate.analyze()
        self._record("midday", payload)
        return payload