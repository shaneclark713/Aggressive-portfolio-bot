from __future__ import annotations


def recent_swing_levels(df, lookback: int = 20):
    window = df.iloc[-lookback - 1 : -1]
    return float(window["high"].max()), float(window["low"].min())
