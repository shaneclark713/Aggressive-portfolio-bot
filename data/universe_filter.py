import logging
from typing import List, Dict, Any

import pandas as pd

from config.universe import (
    CORE_EQUITIES,
    CORE_FUTURES,
    DAY_TRADE_SETTINGS,
    SWING_TRADE_SETTINGS,
)

logger = logging.getLogger("aggressive_portfolio_bot.data.universe_filter")


class UniverseFilter:
    def __init__(self, market_client):
        self.market_client = market_client

    async def build_daily_watchlist(self) -> Dict[str, List[str]]:
        logger.info("Applying universe filters to build today's active watchlists...")

        day_trade_equities: List[str] = []
        swing_trade_equities: List[str] = []

        for symbol in CORE_EQUITIES:
            try:
                df = await self.market_client.get_historical_data(
                    symbol=symbol,
                    multiplier=1,
                    timespan="day",
                    start_date="2025-01-01",
                    end_date="2026-12-31",
                )
            except Exception as e:
                logger.exception("[%s] Failed to fetch historical data: %s", symbol, e)
                continue

            if df.empty or len(df) < 20:
                logger.debug("[%s] Not enough daily data for universe filtering.", symbol)
                continue

            metrics = self._compute_metrics(df, symbol)
            if not metrics:
                continue

            if self._passes_settings(metrics, DAY_TRADE_SETTINGS):
                day_trade_equities.append(symbol)

            if self._passes_settings(metrics, SWING_TRADE_SETTINGS):
                swing_trade_equities.append(symbol)

        logger.info(
            "Universe filter complete. %s day-trade equities, %s swing-trade equities passed.",
            len(day_trade_equities),
            len(swing_trade_equities),
        )

        return {
            "day_trade_equities": sorted(set(day_trade_equities)),
            "swing_trade_equities": sorted(set(swing_trade_equities)),
            "futures": CORE_FUTURES,
        }

    def _compute_metrics(self, df: pd.DataFrame, symbol: str) -> Dict[str, Any]:
        required_cols = {"open", "high", "low", "close", "volume"}
        if not required_cols.issubset(df.columns):
            logger.debug("[%s] Missing required columns for universe metrics.", symbol)
            return {}

        work_df = df[list(required_cols)].dropna().copy()
        if len(work_df) < 20:
            return {}

        atr_series = self._calculate_atr(work_df, period=14)
        if atr_series.empty:
            return {}

        latest = work_df.iloc[-1]
        previous = work_df.iloc[-2]

        current_price = float(latest["close"])
        avg_daily_volume = float(work_df["volume"].tail(20).mean())
        atr_14 = float(atr_series.iloc[-1])

        if pd.isna(atr_14) or current_price <= 0:
            logger.debug("[%s] Invalid ATR or current price.", symbol)
            return {}

        atr_pct = atr_14 / current_price

        prev_close = float(previous["close"])
        gap_pct = abs(float(latest["open"]) - prev_close) / prev_close if prev_close > 0 else 0.0

        return {
            "symbol": symbol,
            "current_price": current_price,
            "avg_daily_volume": avg_daily_volume,
            "atr_pct": atr_pct,
            "gap_pct": gap_pct,
        }

    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        prev_close = df["close"].shift(1)
        tr = pd.concat(
            [
                df["high"] - df["low"],
                (df["high"] - prev_close).abs(),
                (df["low"] - prev_close).abs(),
            ],
            axis=1,
        ).max(axis=1)

        atr = tr.rolling(window=period, min_periods=period).mean().dropna()
        return atr

    def _passes_settings(self, metrics: Dict[str, Any], settings: Dict[str, Any]) -> bool:
        if metrics["current_price"] < settings["min_price"]:
            return False

        if metrics["avg_daily_volume"] < settings["min_avg_daily_volume"]:
            return False

        if metrics["atr_pct"] < settings["min_atr_pct"]:
            return False

        if metrics["gap_pct"] > settings["max_gap_pct"]:
            return False

        return True
