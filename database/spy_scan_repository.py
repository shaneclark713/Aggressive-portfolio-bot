from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime
from typing import Any


class SpyScanJournalRepository:
    """Persistence layer for SPY/XSP desk scan history and outcome analytics."""

    VALID_OUTCOMES = {"win", "loss", "neutral", "skip"}

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

    def mark_outcome(self, scan_id: int, outcome: str, notes: str | None = None) -> dict[str, Any] | None:
        normalized = str(outcome or "").strip().lower()
        if normalized not in self.VALID_OUTCOMES:
            raise ValueError(f"outcome must be one of: {', '.join(sorted(self.VALID_OUTCOMES))}")
        cursor = self.conn.cursor()
        cursor.execute(
            """
            UPDATE spy_scan_journal
            SET outcome = ?, outcome_notes = ?, outcome_marked_at = ?
            WHERE scan_id = ?
            """,
            (normalized, notes or "", datetime.utcnow().isoformat(), int(scan_id)),
        )
        self.conn.commit()
        return self.get_scan(int(scan_id))

    def get_scan(self, scan_id: int) -> dict[str, Any] | None:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM spy_scan_journal WHERE scan_id = ?", (int(scan_id),))
        row = cursor.fetchone()
        return dict(row) if row else None

    def recent_scans(self, limit: int = 10, scan_type: str | None = None, only_marked: bool = False) -> list[dict[str, Any]]:
        cursor = self.conn.cursor()
        filters = []
        params: list[Any] = []
        if scan_type:
            filters.append("scan_type = ?")
            params.append(scan_type)
        if only_marked:
            filters.append("outcome IS NOT NULL")
        where = f"WHERE {' AND '.join(filters)}" if filters else ""
        cursor.execute(
            f"""
            SELECT * FROM spy_scan_journal
            {where}
            ORDER BY scan_id DESC
            LIMIT ?
            """,
            (*params, int(limit)),
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

    def accuracy_summary(self, limit: int = 100) -> dict[str, Any]:
        rows = self.recent_scans(limit=limit, only_marked=True)
        scored = [row for row in rows if row.get("outcome") in {"win", "loss"}]
        wins = [row for row in scored if row.get("outcome") == "win"]
        losses = [row for row in scored if row.get("outcome") == "loss"]
        win_rate = round((len(wins) / len(scored)) * 100.0, 2) if scored else 0.0
        avg_win_conf = round(sum(float(row.get("confidence_score") or 0) for row in wins) / max(len(wins), 1), 2) if wins else 0.0
        avg_loss_conf = round(sum(float(row.get("confidence_score") or 0) for row in losses) / max(len(losses), 1), 2) if losses else 0.0
        return {
            "marked_count": len(rows),
            "scored_count": len(scored),
            "wins": len(wins),
            "losses": len(losses),
            "win_rate": win_rate,
            "avg_win_confidence": avg_win_conf,
            "avg_loss_confidence": avg_loss_conf,
            "rows": rows,
        }

    def _group_summary(self, rows: list[dict[str, Any]], field: str, label_key: str) -> list[dict[str, Any]]:
        buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            label = str(row.get(field) or "unknown")
            buckets[label].append(row)
        summary: list[dict[str, Any]] = []
        for label, items in buckets.items():
            marked = [row for row in items if row.get("outcome")]
            scored = [row for row in items if row.get("outcome") in {"win", "loss"}]
            wins = [row for row in scored if row.get("outcome") == "win"]
            losses = [row for row in scored if row.get("outcome") == "loss"]
            neutrals = [row for row in marked if row.get("outcome") == "neutral"]
            skips = [row for row in marked if row.get("outcome") == "skip"]
            win_rate = round((len(wins) / len(scored)) * 100.0, 2) if scored else 0.0
            avg_conf = round(sum(float(row.get("confidence_score") or 0) for row in scored) / max(len(scored), 1), 2) if scored else 0.0
            avg_structure = round(sum(float(row.get("structure_score") or 0) for row in scored) / max(len(scored), 1), 2) if scored else 0.0
            avg_trend = round(sum(float(row.get("trend_probability") or 0) for row in scored) / max(len(scored), 1), 2) if scored else 0.0
            summary.append({
                label_key: label,
                "marked_count": len(marked),
                "scored_count": len(scored),
                "wins": len(wins),
                "losses": len(losses),
                "neutral": len(neutrals),
                "skip": len(skips),
                "win_rate": win_rate,
                "avg_confidence": avg_conf,
                "avg_structure_score": avg_structure,
                "avg_trend_probability": avg_trend,
            })
        return sorted(summary, key=lambda row: (row["scored_count"], row["win_rate"], row["avg_confidence"]), reverse=True)

    def regime_summary(self, limit: int = 250) -> list[dict[str, Any]]:
        rows = self.recent_scans(limit=limit, only_marked=True)
        return [
            {**row, "dealer_regime": row.pop("dealer_regime_bucket", row.get("dealer_regime", "unknown"))}
            for row in self._group_summary(rows, "dealer_regime", "dealer_regime_bucket")
        ]

    def setup_performance_summary(self, limit: int = 250) -> dict[str, Any]:
        rows = self.recent_scans(limit=limit, only_marked=True)
        scored = [row for row in rows if row.get("outcome") in {"win", "loss"}]
        wins = [row for row in scored if row.get("outcome") == "win"]
        overall_win_rate = round((len(wins) / len(scored)) * 100.0, 2) if scored else 0.0
        return {
            "limit": int(limit),
            "marked_count": len(rows),
            "scored_count": len(scored),
            "wins": len(wins),
            "losses": len(scored) - len(wins),
            "win_rate": overall_win_rate,
            "by_scan_type": self._group_summary(rows, "scan_type", "scan_type"),
            "by_structure_bias": self._group_summary(rows, "structure_bias", "structure_bias"),
            "by_confidence_grade": self._group_summary(rows, "confidence_grade", "confidence_grade"),
            "by_dealer_regime": self._group_summary(rows, "dealer_regime", "dealer_regime"),
        }
