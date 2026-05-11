from __future__ import annotations

from datetime import date, datetime
from html import escape
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd

from data.sentiment import analyze_sentiment


class Spy0DteService:
    """Analysis-only SPY/XSP market-structure report service."""

    def __init__(self, telegram_app, chat_id: int, market_client, news_client, econ_client, tradier_client=None):
        self.telegram_app = telegram_app
        self.chat_id = chat_id
        self.market_client = market_client
        self.news_client = news_client
        self.econ_client = econ_client
        self.tradier_client = tradier_client
        self.market_tz = ZoneInfo("America/New_York")

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

    async def _safe_headlines(self) -> list[dict[str, Any]]:
        try:
            return await self.news_client.fetch_market_news()
        except Exception:
            return []

    async def _safe_events(self) -> list[dict[str, Any]]:
        try:
            return await self.econ_client.fetch_events(date.today())
        except Exception:
            return []

    async def analyze(self) -> dict[str, Any]:
        minute_df = await self.market_client.get_historical_data("SPY", multiplier=5, timespan="minute")
        daily_df = await self.market_client.get_historical_data("SPY", multiplier=1, timespan="day")
        premarket, regular, opening_range = self._today_frames(minute_df)
        active = regular if not regular.empty else premarket if not premarket.empty else minute_df.tail(80)
        latest = self._safe_float(active["close"].iloc[-1]) if not active.empty else self._safe_float(await self.market_client.get_latest_price("SPY"))
        rsi_5m = self._rsi(active["close"]) if not active.empty else 50.0
        rsi_daily = self._rsi(daily_df["close"]) if not daily_df.empty else 50.0
        vwap = self._vwap(regular if not regular.empty else active)
        headlines = await self._safe_headlines()
        events = await self._safe_events()
        structure = self._structure(latest, vwap, rsi_5m, regular, opening_range)
        return {
            "timestamp": datetime.now(self.market_tz).isoformat(timespec="seconds"),
            "latest": latest,
            "vwap": vwap,
            "rsi_5m": rsi_5m,
            "rsi_daily": rsi_daily,
            "premarket_high": self._safe_float(premarket["high"].max()) if not premarket.empty else 0.0,
            "premarket_low": self._safe_float(premarket["low"].min()) if not premarket.empty else 0.0,
            "opening_range_high": self._safe_float(opening_range["high"].max()) if not opening_range.empty else 0.0,
            "opening_range_low": self._safe_float(opening_range["low"].min()) if not opening_range.empty else 0.0,
            "sentiment": analyze_sentiment(headlines),
            "headline_count": len(headlines),
            "top_headlines": self.news_client.summarize_headlines(headlines, limit=4) if hasattr(self.news_client, "summarize_headlines") else [],
            "events": self.econ_client.summarize_events(events, limit=5) if hasattr(self.econ_client, "summarize_events") else [],
            "high_impact_count": len([e for e in events if e.get("impact_label") == "high"]),
            "structure": structure,
        }

    def format_report(self, payload: dict[str, Any], title: str) -> str:
        structure = payload.get("structure", {})
        lines = [
            f"<b>{escape(title)}</b>",
            f"<i>{escape(str(payload.get('timestamp', '')))}</i>",
            "",
            "<b>EXECUTIVE READ</b>",
            f"• Structure: {escape(str(structure.get('bias', 'balanced / tactical')))} | Score: {escape(str(structure.get('score', 0)))}",
            f"• Day Type: {escape(str(structure.get('day_type', 'rotation / mean-reversion structure')))}",
            "",
            "<b>PRICE STRUCTURE</b>",
            f"• SPY Last: {self._price(payload.get('latest'))}",
            f"• VWAP: {self._price(payload.get('vwap'))}",
            f"• Premarket High/Low: {self._price(payload.get('premarket_high'))} / {self._price(payload.get('premarket_low'))}",
            f"• OR Ceiling/Floor: {self._price(payload.get('opening_range_high'))} / {self._price(payload.get('opening_range_low'))}",
            "",
            "<b>RSI / REVERSION</b>",
            f"• 5m RSI: {escape(str(payload.get('rsi_5m')))} | Daily RSI: {escape(str(payload.get('rsi_daily')))}",
            "• Watch RSI extremes for bounce/pullback risk before trusting range continuation.",
            "",
            "<b>CATALYSTS / SENTIMENT</b>",
            f"• Sentiment: {escape(str(payload.get('sentiment', {}).get('sentiment', 'neutral')))} ({payload.get('sentiment', {}).get('score', 0)})",
            f"• Headlines: {payload.get('headline_count')} | High-Impact Events: {payload.get('high_impact_count')}",
        ]
        for event in payload.get("events", [])[:4]:
            lines.append(f"• {escape(str(event))}")
        lines.extend(["", "<b>STRUCTURE NOTES</b>"])
        for item in structure.get("reasons") or ["No strong structure confirmation yet."]:
            lines.append(f"• {escape(str(item))}")
        if payload.get("top_headlines"):
            lines.extend(["", "<b>TOP NEWS</b>"])
            lines.extend(f"• {escape(str(item))}" for item in payload.get("top_headlines", [])[:4])
        return "\n".join(lines)

    async def run_breakdown(self) -> dict[str, Any]:
        payload = await self.analyze()
        await self.telegram_app.bot.send_message(
            chat_id=self.chat_id,
            text=self.format_report(payload, "🧭 6:15 AM SPY/XSP 0DTE Direction Desk"),
            parse_mode="HTML",
        )
        return payload

    async def run_midday(self) -> dict[str, Any]:
        payload = await self.analyze()
        await self.telegram_app.bot.send_message(
            chat_id=self.chat_id,
            text=self.format_report(payload, "☀️ 10:00 AM ET SPY/XSP 0DTE Midday Desk"),
            parse_mode="HTML",
        )
        return payload
