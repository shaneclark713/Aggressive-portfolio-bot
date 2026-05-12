from __future__ import annotations

import json
from datetime import datetime
from typing import Any


class SpyScanJournalRepository:
    """Persistence layer for SPY/XSP desk scan history."""

    def __init__(self, conn):
        self.conn = conn

    def record_scan(self, scan_type: str, payload: dict[str, Any]) -> int:
        structure = payload.get("structure", {}) or {}
        confidence = payload.get("confidence", {}) or {}
        dealer = payload.get("dealer_gamma", {}) or {}
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO spy_scan_journal (
                scan_type,
                created_at,
                symbol,
                latest,
                structure_bias,
                structure_score,
                confidence_grade,
                confidence_score,
                trend_probability,
                mean_reversion_probability,
                dealer_regime,
                dealer_exposure_score,
                payload
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                scan_type,
                payload.get("timestamp") or datetime.utcnow().isoformat(),
                payload.get("symbol", "SPY"),
                payload.get("latest"),
                structure.get("bias"),
                structure.get("score"),
                confidence.get("grade"),
                confidence.get("score"),
                confidence.get("trend_probability"),
                confidence.get("mean_reversion_probability"),
                dealer.get("dealer_regime"),
                dealer.get("exposure_score"),
                json.dumps(payload, default=str),
            ),
        )
        self.conn.commit()
        return int(cursor.lastrowid)

    def recent_scans(self, limit: int = 10, scan_type: str | None = None) -> list[dict[str, Any]]:
        cursor = self.conn.cursor()
        if scan_type:
            cursor.execute(
                """
                SELECT * FROM spy_scan_journal
                WHERE scan_type = ?
                ORDER BY scan_id DESC
                LIMIT ?
                """,
                (scan_type, int(limit)),
            )
        else:
            cursor.execute(
                """
                SELECT * FROM spy_scan_journal
                ORDER BY scan_id DESC
                LIMIT ?
                """,
                (int(limit),),
            )
        return [dict(row) for row in cursor.fetchall()]

    def summarize_recent(self, limit: int = 10) -> dict[str, Any]:
        rows = self.recent_scans(limit=limit)
        if not rows:
            return {"count": 0, "rows": [], "avg_confidence": 0.0, "avg_trend_probability": 0.0}
        confidence_values = [float(row.get("confidence_score") or 0) for row in rows]
        trend_values = [float(row.get("trend_probability") or 0) for row in rows]
        return {
            "count": len(rows),
            "rows": rows,
            "avg_confidence": round(sum(confidence_values) / max(len(confidence_values), 1), 2),
            "avg_trend_probability": round(sum(trend_values) / max(len(trend_values), 1), 2),
        }
