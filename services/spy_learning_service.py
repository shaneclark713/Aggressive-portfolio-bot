from __future__ import annotations

from typing import Any


class SpyLearningService:
    """Summarize what SPY/XSP outcome history suggests should be adjusted.

    This service is advisory only. It does not mutate scoring weights, place orders,
    enable auto-trading, or change risk settings.
    """

    def __init__(self, journal_repo=None):
        self.journal_repo = journal_repo

    def summarize_learning(self, limit: int = 500) -> dict[str, Any]:
        if self.journal_repo is None:
            return {
                "available": False,
                "reason": "SPY/XSP scan journal is not configured.",
                "recommendations": [],
                "warnings": [],
            }
        accuracy = self._safe_call("accuracy_summary", limit=limit, default={})
        performance = self._safe_call("setup_performance_summary", limit=limit, default={})
        calibration = self._safe_call("confidence_calibration_summary", limit=limit, default={})
        recommendations: list[dict[str, Any]] = []
        warnings: list[str] = []

        scored_count = int(accuracy.get("scored_count") or 0)
        if scored_count < 20:
            warnings.append("Learning sample is still small; treat recommendations as directional only.")

        recommendations.extend(self._performance_recommendations(performance))
        recommendations.extend(self._calibration_recommendations(calibration))
        recommendations.extend(self._accuracy_recommendations(accuracy))

        recommendations = sorted(
            recommendations,
            key=lambda row: (row.get("priority", 0), row.get("sample_size", 0)),
            reverse=True,
        )[:12]
        return {
            "available": True,
            "lookback_limit": int(limit),
            "scored_count": scored_count,
            "overall_win_rate": accuracy.get("win_rate", 0.0),
            "recommendations": recommendations,
            "warnings": warnings,
            "performance": performance,
            "calibration": calibration,
        }

    def _performance_recommendations(self, performance: dict[str, Any]) -> list[dict[str, Any]]:
        recs: list[dict[str, Any]] = []
        groups = [
            ("structure_bias", performance.get("by_structure_bias", []) or []),
            ("confidence_grade", performance.get("by_confidence_grade", []) or []),
            ("dealer_regime", performance.get("by_dealer_regime", []) or []),
            ("scan_type", performance.get("by_scan_type", []) or []),
        ]
        for group_name, rows in groups:
            for row in rows:
                sample = int(row.get("scored_count") or 0)
                if sample < 5:
                    continue
                win_rate = float(row.get("win_rate") or 0)
                label = row.get(group_name) or row.get("dealer_regime") or row.get("structure_bias") or row.get("confidence_grade") or row.get("scan_type") or "unknown"
                if win_rate >= 65:
                    recs.append({
                        "type": "increase_weight",
                        "group": group_name,
                        "label": label,
                        "sample_size": sample,
                        "win_rate": win_rate,
                        "priority": 80,
                        "recommendation": f"Increase scoring weight when {group_name} = {label}; historical win rate is {win_rate}%.",
                    })
                elif win_rate <= 40:
                    recs.append({
                        "type": "reduce_weight",
                        "group": group_name,
                        "label": label,
                        "sample_size": sample,
                        "win_rate": win_rate,
                        "priority": 85,
                        "recommendation": f"Reduce or block setups when {group_name} = {label}; historical win rate is only {win_rate}%.",
                    })
        return recs

    def _calibration_recommendations(self, calibration: dict[str, Any]) -> list[dict[str, Any]]:
        recs: list[dict[str, Any]] = []
        for row in calibration.get("buckets", []) or []:
            sample = int(row.get("scored_count") or 0)
            if sample < 5:
                continue
            status = row.get("status")
            bucket = row.get("bucket")
            gap = float(row.get("calibration_gap") or 0)
            if status == "overconfident":
                recs.append({
                    "type": "calibration_downshift",
                    "group": "confidence_bucket",
                    "label": bucket,
                    "sample_size": sample,
                    "win_rate": row.get("actual_win_rate", 0.0),
                    "priority": 90,
                    "recommendation": f"Downshift {bucket} confidence scoring; actual win rate trails projected confidence by {abs(gap)} pts.",
                })
            elif status == "underconfident":
                recs.append({
                    "type": "calibration_upshift",
                    "group": "confidence_bucket",
                    "label": bucket,
                    "sample_size": sample,
                    "win_rate": row.get("actual_win_rate", 0.0),
                    "priority": 70,
                    "recommendation": f"Consider modestly upgrading {bucket} confidence scoring; actual win rate exceeds confidence by {gap} pts.",
                })
        high_conf_losses = calibration.get("high_confidence_losses", []) or []
        if len(high_conf_losses) >= 3:
            recs.append({
                "type": "review_failures",
                "group": "high_confidence_losses",
                "label": "A/high confidence failures",
                "sample_size": len(high_conf_losses),
                "priority": 95,
                "recommendation": "Review recent high-confidence losses for common blockers before trusting A/A+ labels.",
            })
        return recs

    def _accuracy_recommendations(self, accuracy: dict[str, Any]) -> list[dict[str, Any]]:
        scored = int(accuracy.get("scored_count") or 0)
        win_rate = float(accuracy.get("win_rate") or 0.0)
        if scored < 10:
            return []
        if win_rate < 45:
            return [{
                "type": "tighten_filters",
                "group": "overall",
                "label": "all setups",
                "sample_size": scored,
                "win_rate": win_rate,
                "priority": 100,
                "recommendation": "Overall win rate is weak; tighten A+ eligibility and require stronger confirmation before acting.",
            }]
        if win_rate > 60:
            return [{
                "type": "maintain_or_expand",
                "group": "overall",
                "label": "all setups",
                "sample_size": scored,
                "win_rate": win_rate,
                "priority": 60,
                "recommendation": "Overall win rate is constructive; keep current filters and only expand around the best-performing buckets.",
            }]
        return []

    def _safe_call(self, method_name: str, limit: int, default: Any) -> Any:
        method = getattr(self.journal_repo, method_name, None)
        if method is None:
            return default
        try:
            return method(limit=limit)
        except Exception:
            return default
