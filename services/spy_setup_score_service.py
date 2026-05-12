from __future__ import annotations

from typing import Any


class SpySetupScoreService:
    """Score SPY/XSP 0DTE desk setups from scan payloads and historical results.

    This service is analysis-only. It does not place trades or authorize execution.
    """

    def __init__(self, journal_repo=None):
        self.journal_repo = journal_repo

    def score_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        structure = payload.get("structure", {}) or {}
        confidence = payload.get("confidence", {}) or {}
        dealer = payload.get("dealer_gamma", {}) or {}
        data_quality = payload.get("data_quality", {}) or {}

        score = 0
        reasons: list[str] = []
        warnings: list[str] = []

        confidence_score = self._to_float(confidence.get("score"), 0.0)
        structure_score = abs(int(self._to_float(structure.get("score"), 0.0)))
        trend_probability = self._to_float(confidence.get("trend_probability"), 50.0)
        mean_reversion_probability = self._to_float(confidence.get("mean_reversion_probability"), 50.0)
        dealer_regime = str(dealer.get("dealer_regime") or "unknown")
        exposure_score = self._to_float(dealer.get("exposure_score"), 0.0)

        score += min(30, int(confidence_score * 0.30))
        if confidence_score >= 70:
            reasons.append("Desk confidence is A-grade.")
        elif confidence_score >= 55:
            reasons.append("Desk confidence is tradable but not elite.")
        else:
            warnings.append("Desk confidence is below preferred A+ threshold.")

        score += min(25, int(structure_score * 0.45))
        if structure_score >= 45:
            reasons.append("Directional structure is clearly developed.")
        elif structure_score < 25:
            warnings.append("Structure is still balanced or under-confirmed.")

        probability_edge = abs(trend_probability - mean_reversion_probability)
        score += min(15, int(probability_edge * 0.35))
        if probability_edge >= 25:
            reasons.append("Trend/mean-reversion probabilities show a meaningful edge.")
        else:
            warnings.append("Trend and mean-reversion probabilities are close; expect chop risk.")

        if "pin risk" in dealer_regime:
            score -= 10
            warnings.append("Dealer gamma regime warns of pin/mean-reversion risk.")
        elif "hedge pressure" in dealer_regime or "chase pressure" in dealer_regime:
            score += 8
            reasons.append("Dealer regime supports possible expansion/acceleration.")
        elif "balanced" in dealer_regime:
            warnings.append("Dealer regime is balanced; price structure should lead.")

        if abs(exposure_score) >= 35:
            score += 7
            reasons.append("Dealer exposure score is meaningful enough to include in the edge.")

        if data_quality.get("intraday_error"):
            score -= 15
            warnings.append("Intraday data quality is degraded; do not treat this as full A+ confirmation.")
        if payload.get("high_impact_count", 0):
            score -= 5
            warnings.append("High-impact catalyst risk is present.")

        regime_edge = self._historical_regime_edge(dealer_regime)
        if regime_edge:
            score += int(regime_edge.get("score_adjustment", 0))
            note = regime_edge.get("note")
            if note:
                if regime_edge.get("score_adjustment", 0) < 0:
                    warnings.append(str(note))
                else:
                    reasons.append(str(note))

        calibration = self._confidence_calibration(confidence_score)
        if calibration:
            score += int(calibration.get("score_adjustment", 0))
            note = calibration.get("note")
            if note:
                if calibration.get("score_adjustment", 0) < 0:
                    warnings.append(str(note))
                else:
                    reasons.append(str(note))

        score = max(0, min(100, score))
        grade = self._grade(score)
        action = self._action(grade, warnings)
        return {
            "score": score,
            "grade": grade,
            "action": action,
            "reasons": reasons[:6],
            "warnings": warnings[:6],
            "dealer_regime": dealer_regime,
            "confidence_score": confidence_score,
            "structure_score": structure_score,
            "trend_probability": trend_probability,
            "mean_reversion_probability": mean_reversion_probability,
            "calibration": calibration or {},
        }

    def _historical_regime_edge(self, dealer_regime: str) -> dict[str, Any] | None:
        if self.journal_repo is None or not dealer_regime or dealer_regime == "unknown":
            return None
        try:
            regimes = self.journal_repo.regime_summary(limit=250)
        except Exception:
            return None
        for row in regimes:
            if row.get("dealer_regime") != dealer_regime:
                continue
            scored_count = int(row.get("scored_count") or 0)
            win_rate = self._to_float(row.get("win_rate"), 0.0)
            if scored_count < 5:
                return {"score_adjustment": 0, "note": "Historical regime sample is still small."}
            if win_rate >= 65:
                return {"score_adjustment": 8, "note": f"This dealer regime has historically strong results ({win_rate}% win rate)."}
            if win_rate <= 40:
                return {"score_adjustment": -8, "note": f"This dealer regime has historically weak results ({win_rate}% win rate)."}
            return {"score_adjustment": 0, "note": f"This dealer regime is historically mixed ({win_rate}% win rate)."}
        return None

    def _confidence_calibration(self, confidence_score: float) -> dict[str, Any] | None:
        """Compare current confidence bucket against marked historical outcomes."""
        if self.journal_repo is None:
            return None
        try:
            summary = self.journal_repo.accuracy_summary(limit=250)
        except Exception:
            return None
        rows = summary.get("rows", []) or []
        scored = [row for row in rows if row.get("outcome") in {"win", "loss"}]
        if len(scored) < 8:
            return {"score_adjustment": 0, "note": "Confidence calibration sample is still small."}

        low, high, label = self._confidence_bucket(confidence_score)
        bucket = [row for row in scored if low <= self._to_float(row.get("confidence_score"), 0.0) < high]
        if len(bucket) < 5:
            return {"score_adjustment": 0, "note": f"{label} confidence bucket has a small sample."}
        wins = [row for row in bucket if row.get("outcome") == "win"]
        win_rate = round((len(wins) / len(bucket)) * 100.0, 2)
        if win_rate >= 65:
            return {"score_adjustment": 7, "note": f"{label} confidence bucket is historically reliable ({win_rate}% win rate)."}
        if win_rate <= 40:
            return {"score_adjustment": -10, "note": f"{label} confidence bucket has underperformed ({win_rate}% win rate)."}
        return {"score_adjustment": 0, "note": f"{label} confidence bucket is historically mixed ({win_rate}% win rate)."}

    def _confidence_bucket(self, confidence_score: float) -> tuple[float, float, str]:
        if confidence_score >= 70:
            return 70.0, 101.0, "A-grade"
        if confidence_score >= 55:
            return 55.0, 70.0, "B-grade"
        if confidence_score >= 40:
            return 40.0, 55.0, "C-grade"
        return 0.0, 40.0, "Low-grade"

    def _grade(self, score: int) -> str:
        if score >= 85:
            return "A+"
        if score >= 75:
            return "A"
        if score >= 65:
            return "B"
        if score >= 50:
            return "C"
        return "NO-TRADE"

    def _action(self, grade: str, warnings: list[str]) -> str:
        if grade == "A+" and not warnings:
            return "A+ setup: eligible for highest-attention manual execution watch."
        if grade in {"A+", "A"}:
            return "High-quality setup, but respect warnings and confirmation triggers."
        if grade == "B":
            return "Tactical setup only; reduce size or wait for extra confirmation."
        if grade == "C":
            return "Observation setup; wait for cleaner structure."
        return "No-trade / wait."

    def _to_float(self, value: Any, default: float = 0.0) -> float:
        try:
            if value is None:
                return default
            return float(value)
        except Exception:
            return default
