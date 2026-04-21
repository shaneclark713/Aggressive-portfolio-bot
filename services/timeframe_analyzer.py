from __future__ import annotations

from typing import Any, Dict


class TimeframeAnalyzer:
    def summarize(self, intraday_df, daily_df) -> Dict[str, Any]:
        summary = {
            "intraday_trend": "unknown",
            "daily_trend": "unknown",
            "alignment": "mixed",
        }

        if intraday_df is not None and not intraday_df.empty and "close" in intraday_df.columns:
            start = float(intraday_df["close"].iloc[0])
            end = float(intraday_df["close"].iloc[-1])
            summary["intraday_trend"] = "up" if end > start else "down" if end < start else "flat"

        if daily_df is not None and not daily_df.empty and "close" in daily_df.columns:
            idx = max(0, len(daily_df) - 20)
            start = float(daily_df["close"].iloc[idx])
            end = float(daily_df["close"].iloc[-1])
            summary["daily_trend"] = "up" if end > start else "down" if end < start else "flat"

        if summary["intraday_trend"] == summary["daily_trend"] and summary["intraday_trend"] != "flat":
            summary["alignment"] = "aligned"
        elif "unknown" in (summary["intraday_trend"], summary["daily_trend"]):
            summary["alignment"] = "unknown"

        return summary
