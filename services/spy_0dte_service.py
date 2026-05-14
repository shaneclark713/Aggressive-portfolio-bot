from __future__ import annotations

from datetime import date, datetime
from html import escape
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd

from data.sentiment import analyze_sentiment
from services.cross_market_intelligence_service import CrossMarketIntelligenceService
from services.dealer_gamma_service import DealerGammaService


class Spy0DteService:
    """Institutional-style SPY/XSP market-structure report service."""

    US_EVENT_COUNTRIES = {"US", "USA", "UNITED STATES"}
    US_EVENT_KEYWORDS = (
        "ppi", "cpi", "pce", "fed", "fomc", "powell", "claims", "payroll", "nfp",
        "unemployment", "consumer confidence", "ism", "pmi", "retail sales", "auction",
        "treasury", "crude", "oil", "eia", "inventory", "inventories", "gdp",
    )

    def __init__(self, telegram_app, chat_id: int, market_client, news_client, econ_client, tradier_client=None):
        self.telegram_app = telegram_app
        self.chat_id = chat_id
        self.market_client = market_client
        self.news_client = news_client
        self.econ_client = econ_client
        self.tradier_client = tradier_client
        self.market_tz = ZoneInfo("America/New_York")
        self.dealer_gamma = DealerGammaService()
        self.cross_market = CrossMarketIntelligenceService(market_client)

    def _safe_float(self, value: Any, default: float = 0.0) -> float:
        try:
            if value is None or pd.isna(value):
                return default
            return float(value)
        except Exception:
            return default

    def _price(self, value: Any) -> str:
        num = self._safe_float(value)
        return f"${num:.2f}" if num else "n/a"

    def _rsi(self, closes: pd.Series, period: int = 14) -> float:
        closes = closes.dropna()
        if len(closes) < period + 2:
            return 50.0
        delta = closes.diff()
        gains = delta.clip(lower=0).rolling(period).mean()
        losses = (-delta.clip(upper=0)).rolling(period).mean()
        rs = gains / losses.replace(0, pd.NA)
        rsi = 100 - (100 / (1 + rs))
        clean = rsi.dropna()
        return round(float(clean.iloc[-1]), 2) if not clean.empty else 50.0

    def _vwap(self, df: pd.DataFrame) -> float:
        if df.empty or not {"high", "low", "close", "volume"}.issubset(df.columns):
            return 0.0
        volume = df["volume"].fillna(0)
        if float(volume.sum()) <= 0:
            return self._safe_float(df["close"].iloc[-1])
        typical = (df["high"] + df["low"] + df["close"]) / 3
        return round(float((typical * volume).sum() / volume.sum()), 4)

    def _today_frames(self, minute_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        if minute_df.empty:
            return minute_df, minute_df, minute_df
        ny_index = minute_df.index.tz_convert(self.market_tz)
        today = datetime.now(self.market_tz).date()
        today_df = minute_df.loc[ny_index.date == today]
        if today_df.empty:
            return today_df, today_df, today_df
        idx = today_df.index.tz_convert(self.market_tz)
        regular = today_df.loc[((idx.hour > 9) | ((idx.hour == 9) & (idx.minute >= 30))) & (idx.hour < 16)]
        premarket = today_df.loc[(idx.hour >= 4) & ((idx.hour < 9) | ((idx.hour == 9) & (idx.minute < 30)))]
        opening_range = regular.head(6)
        return premarket, regular, opening_range

    def _structure(self, latest: float, vwap: float, rsi: float, regular: pd.DataFrame, opening_range: pd.DataFrame) -> dict[str, Any]:
        score = 0
        reasons: list[str] = []
        if latest and vwap:
            if latest > vwap:
                score += 20
                reasons.append("price above VWAP")
            elif latest < vwap:
                score -= 20
                reasons.append("price below VWAP")
        if 50 <= rsi <= 68:
            score += 15
            reasons.append("RSI supports continuation without full exhaustion")
        elif rsi > 72:
            score -= 10
            reasons.append("RSI stretched; pullback risk elevated")
        elif rsi < 35:
            score -= 10
            reasons.append("RSI weak; bounce needs stabilization first")
        if not opening_range.empty:
            or_high = self._safe_float(opening_range["high"].max())
            or_low = self._safe_float(opening_range["low"].min())
            if latest > or_high:
                score += 20
                reasons.append("price above opening-range ceiling")
            elif latest < or_low:
                score -= 20
                reasons.append("price below opening-range floor")
        if len(regular) >= 3:
            last3 = regular["close"].tail(3)
            if last3.is_monotonic_increasing:
                score += 10
                reasons.append("recent 5m closes stepping higher")
            elif last3.is_monotonic_decreasing:
                score -= 10
                reasons.append("recent 5m closes stepping lower")
        bias = "upside structure" if score >= 25 else "downside structure" if score <= -25 else "balanced / tactical"
        day_type = "trend structure developing" if abs(score) >= 45 else "rotation / mean-reversion structure"
        return {"score": score, "bias": bias, "day_type": day_type, "reasons": reasons[:5]}

    def _market_relevant_events(self, events: list[dict[str, Any]]) -> list[dict[str, Any]]:
        relevant: list[dict[str, Any]] = []
        for event in events or []:
            country = str(event.get("country") or event.get("country_code") or "").strip().upper()
            title = " ".join(str(event.get(key) or "") for key in ("event", "title", "name", "description")).lower()
            if country in self.US_EVENT_COUNTRIES or any(keyword in title for keyword in self.US_EVENT_KEYWORDS):
                relevant.append(event)
        return relevant

    async def _safe_latest_price_any(self, symbols: list[str]) -> tuple[float, str]:
        for symbol in symbols:
            try:
                value = self._safe_float(await self.market_client.get_latest_price(symbol))
                if value > 0:
                    return value, symbol
            except Exception:
                continue
        return 0.0, ""

    async def analyze(self) -> dict[str, Any]:
        minute_df = await self.market_client.get_historical_data("SPY", multiplier=5, timespan="minute")
        daily_df = await self.market_client.get_historical_data("SPY", multiplier=1, timespan="day")

        premarket, regular, opening_range = self._today_frames(minute_df)
        active = regular if not regular.empty else premarket if not premarket.empty else minute_df.tail(80)

        latest = self._safe_float(active["close"].iloc[-1]) if not active.empty else 0.0
        prev_close = self._safe_float(daily_df["close"].dropna().iloc[-2]) if not daily_df.empty and len(daily_df["close"].dropna()) >= 2 else 0.0

        rsi_5m = self._rsi(active["close"]) if not active.empty else 50.0
        rsi_daily = self._rsi(daily_df["close"]) if not daily_df.empty else 50.0
        vwap = self._vwap(regular if not regular.empty else active)

        headlines = await self.news_client.fetch_market_news() if self.news_client else []
        raw_events = await self.econ_client.fetch_events(date.today()) if self.econ_client else []
        events = self._market_relevant_events(raw_events)

        chain_rows = []
        if self.tradier_client and hasattr(self.tradier_client, "get_options_chain"):
            try:
                rows = await self.tradier_client.get_options_chain(symbol="SPY", expiration=date.today().isoformat(), greeks=True)
                chain_rows = rows if isinstance(rows, list) else []
            except Exception:
                chain_rows = []

        dealer_gamma = self.dealer_gamma.summarize(latest, chain_rows).as_dict()
        structure = self._structure(latest, vwap, rsi_5m, regular, opening_range)

        xsp_latest, xsp_symbol = await self._safe_latest_price_any(["XSP", "I:XSP", "CBOE:XSP"])
        spx_latest, spx_symbol = await self._safe_latest_price_any(["I:SPX", "SPX", "CBOE:SPX"])

        cross_market = await self.cross_market.analyze()

        return {
            "timestamp": datetime.now(self.market_tz).isoformat(timespec="seconds"),
            "latest": latest,
            "prev_close": prev_close,
            "vwap": vwap,
            "rsi_5m": rsi_5m,
            "rsi_daily": rsi_daily,
            "xsp_latest": xsp_latest,
            "spx_latest": spx_latest,
            "xsp_symbol_used": xsp_symbol,
            "spx_symbol_used": spx_symbol,
            "premarket_high": self._safe_float(premarket["high"].max()) if not premarket.empty else 0.0,
            "premarket_low": self._safe_float(premarket["low"].min()) if not premarket.empty else 0.0,
            "opening_range_high": self._safe_float(opening_range["high"].max()) if not opening_range.empty else 0.0,
            "opening_range_low": self._safe_float(opening_range["low"].min()) if not opening_range.empty else 0.0,
            "sentiment": analyze_sentiment(headlines),
            "events": events,
            "zones": dealer_gamma,
            "dealer_gamma": dealer_gamma,
            "structure": structure,
            "cross_market": cross_market,
        }
