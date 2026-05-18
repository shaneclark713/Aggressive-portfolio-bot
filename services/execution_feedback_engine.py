from __future__ import annotations

from typing import Any


class ExecutionFeedbackEngine:
    """Execution intelligence feedback loop.

    Tracks execution quality and converts fills into adaptation signals.
    Advisory only; downstream memory/ecosystem layers consume the output.
    """

    def evaluate(self, payload: dict[str, Any]) -> dict[str, Any]:
        fill_quality = int(payload.get("fill_quality", 50) or 50)
        slippage = float(payload.get("slippage_bps", 0) or 0)
        hold_efficiency = int(payload.get("hold_efficiency", 50) or 50)
        scaling_efficiency = int(payload.get("scaling_efficiency", 50) or 50)
        exit_precision = int(payload.get("exit_precision", 50) or 50)

        execution_score = int(
            fill_quality * 0.25
            + hold_efficiency * 0.20
            + scaling_efficiency * 0.20
            + exit_precision * 0.20
            + max(0, 100 - min(100, int(slippage))) * 0.15
        )

        adaptation = "maintain"
        if execution_score >= 75:
            adaptation = "expand"
        elif execution_score <= 45:
            adaptation = "tighten"

        return {
            "execution_score": max(0, min(100, execution_score)),
            "adaptation_signal": adaptation,
            "feedback_label": "EXECUTION_ALIGNED" if execution_score >= 70 else "EXECUTION_REVIEW",
            "metrics": {
                "fill_quality": fill_quality,
                "slippage_bps": slippage,
                "hold_efficiency": hold_efficiency,
                "scaling_efficiency": scaling_efficiency,
                "exit_precision": exit_precision,
            },
        }
