from __future__ import annotations

import pandas as pd


def ema(series: pd.Series, length: int) -> pd.Series:
    return series.ewm(span=length, adjust=False).mean()


def sma(series: pd.Series, length: int) -> pd.Series:
    return series.rolling(window=length, min_periods=length).mean()


def atr(df: pd.DataFrame, length: int = 14) -> pd.Series:
    prev_close = df["close"].shift(1)
    tr = pd.concat(
        [
            df["high"] - df["low"],
            (df["high"] - prev_close).abs(),
            (df["low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.rolling(window=length, min_periods=length).mean()


def rsi(close: pd.Series, length: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=length, min_periods=length).mean()
    avg_loss = loss.rolling(window=length, min_periods=length).mean()
    rs = avg_gain / avg_loss.replace(0, pd.NA)
    return (100 - (100 / (1 + rs))).fillna(50).clip(lower=0, upper=100)


def adx(df: pd.DataFrame, length: int = 14) -> pd.Series:
    high = df["high"]
    low = df["low"]
    up_move = high.diff()
    down_move = -low.diff()

    plus_dm = pd.Series(
        [
            up if pd.notna(up) and pd.notna(down) and up > down and up > 0 else 0.0
            for up, down in zip(up_move, down_move)
        ],
        index=df.index,
        dtype="float64",
    )
    minus_dm = pd.Series(
        [
            down if pd.notna(up) and pd.notna(down) and down > up and down > 0 else 0.0
            for up, down in zip(up_move, down_move)
        ],
        index=df.index,
        dtype="float64",
    )

    atr_series = atr(df, length)
    plus_di = 100 * (plus_dm.rolling(window=length, min_periods=length).mean() / atr_series)
    minus_di = 100 * (minus_dm.rolling(window=length, min_periods=length).mean() / atr_series)
    dx = ((plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, pd.NA)) * 100
    return dx.rolling(window=length, min_periods=length).mean()


def bollinger_bands(close: pd.Series, length: int = 20, std_mult: float = 2.0) -> pd.DataFrame:
    mid = close.rolling(window=length, min_periods=length).mean()
    std = close.rolling(window=length, min_periods=length).std(ddof=0)
    lower = mid - std * std_mult
    upper = mid + std * std_mult
    return pd.DataFrame({"lower": lower, "mid": mid, "upper": upper}, index=close.index)


def volume_ratio(volume: pd.Series, length: int = 20) -> pd.Series:
    baseline = volume.rolling(window=length, min_periods=length).mean()
    return volume / baseline.replace(0, pd.NA)


def percent_change(series: pd.Series, periods: int = 1) -> pd.Series:
    return series.pct_change(periods=periods) * 100.0
