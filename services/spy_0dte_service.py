from __future__ import annotations

from datetime import date, datetime
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd

from data.sentiment import analyze_sentiment
from services.adaptive_exit_engine import AdaptiveExitEngine
from services.autonomous_scaling_engine import AutonomousScalingEngine
from services.cross_market_intelligence_service import CrossMarketIntelligenceService
from services.dealer_gamma_service import DealerGammaService
from services.execution_timing_engine import ExecutionTimingEngine
from services.market_narrative_engine import MarketNarrativeEngine
from services.probability_matrix_engine import ProbabilityMatrixEngine
from services.session_personality_engine import SessionPersonalityEngine
from services.tactical_playbook_engine import TacticalPlaybookEngine
from services.trade_memory_engine import TradeMemoryEngine
from services.trap_detection_engine import TrapDetectionEngine


class Spy0DteService:
    """Institutional-style SPY/XSP tactical intelligence service."""

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
        self.narrative_engine = MarketNarrativeEngine()
        self.playbook_engine = TacticalPlaybookEngine()
        self.probability_engine = ProbabilityMatrixEngine()
        self.execution_timing_engine = ExecutionTimingEngine()
        self.adaptive_exit_engine = AdaptiveExitEngine()
        self.autonomous_scaling_engine = AutonomousScalingEngine()
        self.session_personality_engine = SessionPersonalityEngine()
        self.trap_detection_engine = TrapDetectionEngine()
        self.trade_memory_engine = TradeMemoryEngine()

    def _safe_float(self, value: Any, default: float = 0.0) -> float:
        try:
            if value is None or pd.isna(value):
                return default
            return float(value)
        except Exception:
            return default

    async def _safe_latest_price_any(self, symbols: list[str]) -> tuple[float, str]:
        for symbol in symbols:
            try:
                value = self._safe_float(await self.market_client.get_latest_price(symbol))
                if value > 0:
                    return value, symbol
            except Exception:
                continue
        return 0.0, ""

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

    def _today_frames(self, minute_df: pd.DataFrame):
        if minute_df.empty:
            return minute_df, minute_df, minute_df

        ny_index = minute_df.index.tz_convert(self.market_tz)
        today = datetime.now(self.market_tz).date()
        today_df = minute_df.loc[ny_index.date == today]

        idx = today_df.index.tz_convert(self.market_tz)

        regular = today_df.loc[
            ((idx.hour > 9) | ((idx.hour == 9) & (idx.minute >= 30)))
            & (idx.hour < 16)
        ]

        premarket = today_df.loc[
            (idx.hour >= 4)
            & ((idx.hour < 9) | ((idx.hour == 9) & (idx.minute < 30)))
        ]

        opening_range = regular.head(6)
        return premarket, regular, opening_range

    def _market_relevant_events(self, events: list[dict[str, Any]]) -> list[dict[str, Any]]:
        relevant: list[dict[str, Any]] = []

        for event in events or []:
            country = str(event.get("country") or "").upper()
            title = str(event.get("event") or event.get("title") or "").lower()

            if country in self.US_EVENT_COUNTRIES or any(k in title for k in self.US_EVENT_KEYWORDS):
                relevant.append(event)

        return relevant

    def _structure(self, latest: float, vwap: float, rsi: float, opening_range: pd.DataFrame) -> dict[str, Any]:
        score = 0
        reasons: list[str] = []

        if latest > vwap:
            score += 20
            reasons.append("price above VWAP")
        elif latest < vwap:
            score -= 20
            reasons.append("price below VWAP")

        if 50 <= rsi <= 68:
            score += 15
            reasons.append("RSI supports continuation")
        elif rsi > 72:
            score -= 10
            reasons.append("RSI stretched")

        if not opening_range.empty:
            or_high = self._safe_float(opening_range["high"].max())
            or_low = self._safe_float(opening_range["low"].min())

            if latest > or_high:
                score += 20
                reasons.append("above opening range")
            elif latest < or_low:
                score -= 20
                reasons.append("below opening range")

        bias = "upside structure" if score >= 25 else "downside structure" if score <= -25 else "balanced / tactical"

        return {
            "score": score,
            "bias": bias,
            "reasons": reasons[:5],
        }

    async def analyze(self) -> dict[str, Any]:
        minute_df = await self.market_client.get_historical_data("SPY", multiplier=5, timespan="minute")
        daily_df = await self.market_client.get_historical_data("SPY", multiplier=1, timespan="day")

        premarket, regular, opening_range = self._today_frames(minute_df)
        active = regular if not regular.empty else premarket

        latest = self._safe_float(active["close"].iloc[-1]) if not active.empty else 0.0
        prev_close = self._safe_float(daily_df["close"].dropna().iloc[-2]) if not daily_df.empty else 0.0

        rsi_5m = self._rsi(active["close"]) if not active.empty else 50.0
        vwap = self._vwap(regular if not regular.empty else active)

        headlines = await self.news_client.fetch_market_news() if self.news_client else []
        raw_events = await self.econ_client.fetch_events(date.today()) if self.econ_client else []
        events = self._market_relevant_events(raw_events)

        chain_rows = []

        if self.tradier_client and hasattr(self.tradier_client, "get_options_chain"):
            try:
                chain_rows = await self.tradier_client.get_options_chain(
                    symbol="SPY",
                    expiration=date.today().isoformat(),
                    greeks=True,
                )
            except Exception:
                chain_rows = []

        dealer_gamma = self.dealer_gamma.summarize(
            latest,
            chain_rows if isinstance(chain_rows, list) else [],
        ).as_dict()

        structure = self._structure(
            latest,
            vwap,
            rsi_5m,
            opening_range,
        )

        xsp_latest, xsp_symbol = await self._safe_latest_price_any([
            "XSP",
            "I:XSP",
            "CBOE:XSP",
        ])

        spx_latest, spx_symbol = await self._safe_latest_price_any([
            "I:SPX",
            "SPX",
            "CBOE:SPX",
        ])

        cross_market = await self.cross_market.analyze()
        sentiment = analyze_sentiment(headlines)

        narrative = self.narrative_engine.build(
            structure=structure,
            dealer_gamma=dealer_gamma,
            cross_market=cross_market,
            sentiment=sentiment,
            rsi_5m=rsi_5m,
            latest=latest,
            vwap=vwap,
        )

        playbook = self.playbook_engine.select(
            structure=structure,
            dealer_gamma=dealer_gamma,
            cross_market=cross_market,
            narrative=narrative,
            rsi_5m=rsi_5m,
            latest=latest,
            vwap=vwap,
        )

        probabilities = self.probability_engine.build(
            structure=structure,
            dealer_gamma=dealer_gamma,
            cross_market=cross_market,
            narrative=narrative,
            playbook=playbook,
            rsi_5m=rsi_5m,
            latest=latest,
            vwap=vwap,
        )

        execution_timing = self.execution_timing_engine.analyze(
            structure=structure,
            probabilities=probabilities,
            latest=latest,
            vwap=vwap,
        )

        adaptive_exits = self.adaptive_exit_engine.evaluate(
            probabilities=probabilities,
            playbook=playbook,
            structure=structure,
            execution_timing=execution_timing,
            rsi_5m=rsi_5m,
            latest=latest,
            vwap=vwap,
        )

        autonomous_scaling = self.autonomous_scaling_engine.plan(
            probabilities=probabilities,
            playbook=playbook,
            adaptive_exits=adaptive_exits,
            execution_timing=execution_timing,
            rsi_5m=rsi_5m,
        )

        session_personality = self.session_personality_engine.classify(
            probabilities=probabilities,
            structure=structure,
            dealer_gamma=dealer_gamma,
            execution_timing=execution_timing,
            latest=latest,
            vwap=vwap,
            rsi_5m=rsi_5m,
        )

        trap_detection = self.trap_detection_engine.detect(
            probabilities=probabilities,
            structure=structure,
            session_personality=session_personality,
            execution_timing=execution_timing,
            latest=latest,
            vwap=vwap,
            rsi_5m=rsi_5m,
        )

        trade_memory = self.trade_memory_engine.snapshot(
            playbook=playbook,
            session_personality=session_personality,
            trap_detection=trap_detection,
            probabilities=probabilities,
        )

        return {
            "timestamp": datetime.now(self.market_tz).isoformat(timespec="seconds"),
            "latest": latest,
            "prev_close": prev_close,
            "vwap": vwap,
            "rsi_5m": rsi_5m,
            "xsp_latest": xsp_latest,
            "spx_latest": spx_latest,
            "xsp_symbol_used": xsp_symbol,
            "spx_symbol_used": spx_symbol,
            "sentiment": sentiment,
            "events": events,
            "dealer_gamma": dealer_gamma,
            "structure": structure,
            "cross_market": cross_market,
            "narrative": narrative,
            "playbook": playbook,
            "probabilities": probabilities,
            "confidence": confidence,
            "execution_timing": execution_timing,
            "adaptive_exits": adaptive_exits,
            "autonomous_scaling": autonomous_scaling,
            "session_personality": session_personality,
            "trap_detection": trap_detection,
            "trade_memory": trade_memory,
        }
