from __future__ import annotations

import logging
from typing import List, Dict, Any

import pandas as pd

from config.universe import CORE_EQUITIES, CORE_FUTURES, DAY_TRADE_SETTINGS, SWING_TRADE_SETTINGS

logger = logging.getLogger("aggressive_portfolio_bot.data.universe_filter")


class UniverseFilter:
    def __init__(self, market_client):
        self.market_client = market_client
        self._last_watchlist_stats: Dict[str, Any] = {}

    def get_last_watchlist_stats(self) -> Dict[str, Any]:
        return dict(self._last_watchlist_stats)

    async def build_daily_watchlist(self) -> Dict[str, List[str]]:
        logger.info("Applying universe filters to build today's active watchlists...")

        day_trade_equities: List[str] = []
        swing_trade_equities: List[str] = []
        fetched = 0
        passed_day = 0
        passed_swing = 0
        errors = 0

        for symbol in CORE_EQUITIES:
            try:
                df = await self.market_client.get_historical_data(
                    symbol=symbol,
                    multiplier=1,
                    timespan="day",
                )
            except Exception as exc:
                errors += 1
                logger.exception("[%s] Failed to fetch historical data: %s", symbol, exc)
                continue

            if df.empty or len(df) < 20:
                logger.debug("[%s] Not enough daily data for universe filtering.", symbol)
                continue

            fetched += 1
            metrics = self._compute_metrics(df, symbol)
            if not metrics:
                continue

            if self._passes_settings(metrics, DAY_TRADE_SETTINGS):
                day_trade_equities.append(symbol)
                passed_day += 1

            if self._passes_settings(metrics, SWING_TRADE_SETTINGS):
                swing_trade_equities.append(symbol)
                passed_swing += 1

        self._last_watchlist_stats = {
            "symbols_considered": len(CORE_EQUITIES),
            "symbols_fetched": fetched,
            "day_trade_count": passed_day,
            "swing_trade_count": passed_swing,
            "errors": errors,
        }

        logger.info(
            "Universe filter complete. day=%s swing=%s fetched=%s errors=%s",
            passed_day,
            passed_swing,
            fetched,
            errors,
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

        work_df = df[["open", "high", "low", "close", "volume"]].dropna().copy()
        if len(work_df) < 20:
            return {}

        atr_series = self._calculate_atr(work_df, period=14)
        if atr_series.empty:
            return {}

        latest = work_df.iloc[-1]
        previous = work_df.iloc[-2]

        current_price = float(latest["close"])
        avg_daily_volume = float(work_df["volume"].tail(20).mean())
        avg_dollar_volume = float((work_df["close"] * work_df["volume"]).tail(20).mean())
        atr_14 = float(atr_series.iloc[-1])

        if pd.isna(atr_14) or current_price <= 0:
            logger.debug("[%s] Invalid ATR or current price.", symbol)
            return {}

        prev_close = float(previous["close"])
        open_gap_pct = abs(float(latest["open"]) - prev_close) / prev_close if prev_close > 0 else 0.0
        day_range_pct = abs(float(latest["high"]) - float(latest["low"])) / current_price if current_price > 0 else 0.0

        return {
            "symbol": symbol,
            "current_price": round(current_price, 2),
            "avg_daily_volume": round(avg_daily_volume, 0),
            "avg_dollar_volume": round(avg_dollar_volume, 0),
            "atr_pct": round(atr_14 / current_price, 4) if current_price > 0 else 0.0,
            "open_gap_pct": round(open_gap_pct, 4),
            "day_range_pct": round(day_range_pct, 4),
        }

    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        prev_close = df["close"].shift(1)
        tr = pd.concat([
            df["high"] - df["low"],
            (df["high"] - prev_close).abs(),
            (df["low"] - prev_close).abs(),
        ], axis=1).max(axis=1)
        return tr.rolling(window=period, min_periods=period).mean().dropna()

    def _passes_settings(self, metrics: Dict[str, Any], settings: Dict[str, Any]) -> bool:
        checks = [
            metrics["current_price"] >= settings["min_price"],
            metrics["avg_daily_volume"] >= settings["min_avg_daily_volume"],
            metrics["atr_pct"] >= settings["min_atr_pct"],
            metrics["open_gap_pct"] <= settings["max_gap_pct"],
        ]
        return all(checks)
