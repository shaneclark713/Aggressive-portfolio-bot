import pandas as pd


class MarketRegimeClassifier:
    def _adx(self, df: pd.DataFrame, length: int = 14) -> pd.Series:
        high = df["high"]
        low = df["low"]
        close = df["close"]

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

        prev_close = close.shift(1)
        tr = pd.concat(
            [
                high - low,
                (high - prev_close).abs(),
                (low - prev_close).abs(),
            ],
            axis=1,
        ).max(axis=1)

        atr = tr.rolling(window=length, min_periods=length).mean()
        plus_di = 100 * (plus_dm.rolling(window=length, min_periods=length).mean() / atr)
        minus_di = 100 * (minus_dm.rolling(window=length, min_periods=length).mean() / atr)

        dx = ((plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, pd.NA)) * 100
        adx = dx.rolling(window=length, min_periods=length).mean()
        return adx

    def classify(self, df: pd.DataFrame) -> str:
        required_cols = {"high", "low", "close"}
        if df.empty or len(df) < 30 or not required_cols.issubset(df.columns):
            return "UNKNOWN"

        work = df[["high", "low", "close"]].dropna().copy()
        if len(work) < 30:
            return "UNKNOWN"

        adx_series = self._adx(work, length=14).dropna()
        if adx_series.empty:
            return "UNKNOWN"

        adx_value = float(adx_series.iloc[-1])
        return "TREND" if adx_value >= 20 else "RANGE"
