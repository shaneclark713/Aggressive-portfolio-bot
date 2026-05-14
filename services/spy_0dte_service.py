from __future__ import annotations

from datetime import date, datetime
from html import escape
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd

from data.sentiment import analyze_sentiment
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

    def _opening_drive(self, latest: float, regular: pd.DataFrame, opening_range: pd.DataFrame) -> str:
        if regular.empty or opening_range.empty:
            return "opening range not formed yet"
        or_high = self._safe_float(opening_range["high"].max())
        or_low = self._safe_float(opening_range["low"].min())
        if latest > or_high:
            return "accepted above opening-range ceiling"
        if latest < or_low:
            return "accepted below opening-range floor"
        return "inside opening range / auction still balanced"

    def _volume_nodes(self, regular: pd.DataFrame) -> list[str]:
        if regular.empty or "volume" not in regular.columns:
            return ["Volume profile unavailable until regular-session data loads."]
        work = regular.dropna(subset=["close"]).copy()
        if work.empty:
            return ["Volume profile unavailable."]
        rounded = (work["close"] / 0.5).round() * 0.5
        grouped = work.groupby(rounded)["volume"].sum().sort_values(ascending=False).head(3)
        return [f"{price:.2f} high-volume node" for price in grouped.index]

    def _sweep_notes(self, latest: float, vwap: float, rsi: float, opening_range: pd.DataFrame) -> list[str]:
        if opening_range.empty:
            return ["Opening-range sweep detection waiting for first 30 minutes of data."]
        or_high = self._safe_float(opening_range["high"].max())
        or_low = self._safe_float(opening_range["low"].min())
        notes: list[str] = []
        if latest > or_high and rsi > 72:
            notes.append("Upside range break is stretched; watch for failed-break pullback.")
        elif latest > or_high and latest > vwap:
            notes.append("Upside range break has VWAP confirmation.")
        if latest < or_low and rsi < 30:
            notes.append("Downside range break is stretched; watch for reflex bounce.")
        elif latest < or_low and latest < vwap:
            notes.append("Downside range break has VWAP confirmation.")
        if not notes:
            notes.append("No clean range sweep detected yet.")
        return notes

    def _volatility_state(self, regular: pd.DataFrame, opening_range: pd.DataFrame) -> str:
        if regular.empty or opening_range.empty:
            return "unknown until opening range forms"
        or_range = self._safe_float(opening_range["high"].max()) - self._safe_float(opening_range["low"].min())
        latest_range = self._safe_float(regular["high"].max()) - self._safe_float(regular["low"].min())
        if or_range <= 0:
            return "compressed"
        expansion = latest_range / or_range
        if expansion >= 1.8:
            return "expanding"
        if expansion <= 1.15:
            return "compressed / pinned"
        return "normal intraday expansion"

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

    def _cross_confirmation(self, spy_latest: float, spy_prev_close: float, spy_structure: dict[str, Any], xsp_latest: float, spx_latest: float) -> dict[str, Any]:
        spy_change = ((spy_latest - spy_prev_close) / spy_prev_close * 100.0) if spy_latest and spy_prev_close else 0.0
        notes: list[str] = []
        confirmations = 0
        if xsp_latest:
            spread_pct = ((xsp_latest - spy_latest) / spy_latest * 100.0) if spy_latest else 0.0
            if abs(spread_pct) <= 0.35:
                confirmations += 1
                notes.append("XSP is aligned with SPY price structure.")
            else:
                notes.append(f"XSP divergence detected ({spread_pct:.2f}%).")
        else:
            notes.append("XSP live price unavailable; using SPY primary structure.")
        if spx_latest:
            spx_proxy = spx_latest / 10
            spread_pct = ((spx_proxy - spy_latest) / spy_latest * 100.0) if spy_latest else 0.0
            if abs(spread_pct) <= 0.35:
                confirmations += 1
                notes.append("SPX proxy is aligned with SPY price structure.")
            else:
                notes.append(f"SPX proxy divergence detected ({spread_pct:.2f}%).")
        else:
            notes.append("SPX live price unavailable; no index cross-check included.")
        if spy_structure.get("bias") == "balanced / tactical":
            state = "neutral confirmation"
        elif confirmations >= 1:
            state = "confirmed"
        else:
            state = "unconfirmed"
        return {"state": state, "confirmations": confirmations, "spy_change_pct": round(spy_change, 2), "notes": notes[:4]}

    def _confidence(self, payload: dict[str, Any]) -> dict[str, Any]:
        structure = payload.get("structure", {})
        cross = payload.get("cross_confirmation", {})
        dealer = payload.get("dealer_gamma", {})
        score = abs(int(structure.get("score", 0)))
        notes: list[str] = []
        if structure.get("bias") != "balanced / tactical":
            score += 10
            notes.append("Directional structure is not neutral.")
        if cross.get("state") == "confirmed":
            score += 15
            notes.append("SPY structure has index cross-confirmation.")
        elif cross.get("state") == "unconfirmed":
            score -= 10
            notes.append("Index cross-confirmation is missing or divergent.")
        vol_state = str(payload.get("volatility_state", ""))
        if "normal" in vol_state or "expanding" in vol_state:
            score += 10
            notes.append("Volatility state supports tradable movement.")
        elif "compressed" in vol_state:
            score -= 10
            notes.append("Compressed volatility raises chop/pin risk.")
        dealer_regime = str(dealer.get("dealer_regime", ""))
        if "pin risk" in dealer_regime:
            score -= 10
            notes.append("Dealer gamma layer warns of pin/mean-reversion risk.")
        elif "hedge pressure" in dealer_regime:
            score += 5
            notes.append("Dealer gamma layer shows potential acceleration pressure.")
        elif "chase pressure" in dealer_regime:
            score += 5
            notes.append("Dealer gamma layer shows potential squeeze/chase pressure.")
        rsi = self._safe_float(payload.get("rsi_5m"), 50.0)
        if 40 <= rsi <= 68:
            score += 10
            notes.append("RSI is in a usable continuation/reversion band.")
        elif rsi > 75 or rsi < 25:
            score -= 10
            notes.append("RSI is extreme; wait for stabilization or pullback confirmation.")
        if int(payload.get("high_impact_count", 0) or 0) > 0:
            score -= 5
            notes.append("High-impact U.S./market events increase headline risk.")
        score = max(0, min(100, score))
        grade = "A" if score >= 70 else "B" if score >= 55 else "C" if score >= 40 else "NO-TRADE / WAIT"
        trend_probability = max(20, min(80, 50 + int(structure.get("score", 0)) // 2))
        if "pin risk" in dealer_regime:
            trend_probability = max(20, trend_probability - 10)
        elif "hedge pressure" in dealer_regime or "chase pressure" in dealer_regime:
            trend_probability = min(80, trend_probability + 5)
        mean_reversion_probability = 100 - trend_probability
        return {"score": score, "grade": grade, "trend_probability": trend_probability, "mean_reversion_probability": mean_reversion_probability, "notes": notes[:6]}

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

    async def _safe_chain_rows(self, symbol: str = "SPY") -> list[dict[str, Any]]:
        if self.tradier_client is None or not hasattr(self.tradier_client, "get_options_chain"):
            return []
        try:
            expiration = date.today().isoformat()
            if hasattr(self.tradier_client, "get_expirations"):
                expirations = await self.tradier_client.get_expirations(symbol)
                if expirations:
                    expiration = expirations[0]
            rows = await self.tradier_client.get_options_chain(symbol=symbol, expiration=expiration, greeks=True)
            return rows if isinstance(rows, list) else []
        except Exception:
            return []

    async def analyze(self) -> dict[str, Any]:
        minute_df = await self.market_client.get_historical_data("SPY", multiplier=5, timespan="minute")
        daily_df = await self.market_client.get_historical_data("SPY", multiplier=1, timespan="day")
        premarket, regular, opening_range = self._today_frames(minute_df)
        active = regular if not regular.empty else premarket if not premarket.empty else minute_df.tail(80)
        latest = self._safe_float(active["close"].iloc[-1]) if not active.empty else self._safe_float(await self.market_client.get_latest_price("SPY"))
        prev_close = self._safe_float(daily_df["close"].dropna().iloc[-2]) if not daily_df.empty and len(daily_df["close"].dropna()) >= 2 else 0.0
        rsi_5m = self._rsi(active["close"]) if not active.empty else 50.0
        rsi_daily = self._rsi(daily_df["close"]) if not daily_df.empty else 50.0
        vwap = self._vwap(regular if not regular.empty else active)
        headlines = await self._safe_headlines()
        raw_events = await self._safe_events()
        events = self._market_relevant_events(raw_events)
        chain_rows = await self._safe_chain_rows("SPY")
        dealer_gamma = self.dealer_gamma.summarize(latest, chain_rows).as_dict()
        structure = self._structure(latest, vwap, rsi_5m, regular, opening_range)
        xsp_latest, xsp_symbol = await self._safe_latest_price_any(["XSP", "I:XSP", "CBOE:XSP"])
        spx_latest, spx_symbol = await self._safe_latest_price_any(["I:SPX", "SPX", "CBOE:SPX"])
        summarized_events = self.econ_client.summarize_events(events, limit=5) if hasattr(self.econ_client, "summarize_events") else []
        high_impact_count = len([e for e in events if str(e.get("impact_label") or "").lower() == "high"])
        payload = {
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
            "opening_drive": self._opening_drive(latest, regular, opening_range),
            "volatility_state": self._volatility_state(regular, opening_range),
            "volume_nodes": self._volume_nodes(regular),
            "sweep_notes": self._sweep_notes(latest, vwap, rsi_5m, opening_range),
            "sentiment": analyze_sentiment(headlines),
            "headline_count": len(headlines),
            "top_headlines": self.news_client.summarize_headlines(headlines, limit=4) if hasattr(self.news_client, "summarize_headlines") else [],
            "events": summarized_events,
            "raw_event_count": len(raw_events),
            "market_event_count": len(events),
            "high_impact_count": high_impact_count,
            "chain_contracts": len(chain_rows),
            "zones": dealer_gamma,
            "dealer_gamma": dealer_gamma,
            "structure": structure,
        }
        payload["cross_confirmation"] = self._cross_confirmation(latest, prev_close, structure, xsp_latest, spx_latest)
        payload["confidence"] = self._confidence(payload)
        return payload

    def _desk_bias(self, payload: dict[str, Any]) -> str:
        structure = payload.get("structure", {})
        confidence = payload.get("confidence", {})
        dealer = str(payload.get("dealer_gamma", {}).get("dealer_regime", ""))
        latest = self._safe_float(payload.get("latest"))
        vwap = self._safe_float(payload.get("vwap"))
        score = int(structure.get("score", 0) or 0)
        if confidence.get("grade") == "NO-TRADE / WAIT":
            return "WAIT / NO CLEAN EDGE"
        if score >= 25 and latest >= vwap and "pin risk" not in dealer:
            return "CALLS FAVORED ABOVE VWAP / OR HIGH"
        if score <= -25 and latest <= vwap:
            return "PUTS FAVORED BELOW VWAP / OR LOW"
        return "TACTICAL / RANGE SCALP ONLY"

    def _execution_plan(self, payload: dict[str, Any]) -> list[str]:
        latest = self._safe_float(payload.get("latest"))
        vwap = self._safe_float(payload.get("vwap"))
        or_high = self._safe_float(payload.get("opening_range_high"))
        or_low = self._safe_float(payload.get("opening_range_low"))
        structure = payload.get("structure", {})
        confidence = payload.get("confidence", {})
        lines = [
            f"Primary Bias: {self._desk_bias(payload)}",
            f"Trend Day Probability: {confidence.get('trend_probability', 50)}%",
            f"Mean-Reversion Probability: {confidence.get('mean_reversion_probability', 50)}%",
        ]
        if vwap:
            lines.append(f"Call confirmation requires price holding above VWAP {self._price(vwap)}.")
            lines.append(f"Put confirmation requires VWAP rejection or loss below {self._price(vwap)}.")
        if or_high:
            lines.append(f"Bullish trigger: acceptance above OR ceiling {self._price(or_high)}.")
        if or_low:
            lines.append(f"Bearish trigger: acceptance below OR floor {self._price(or_low)}.")
        if latest and or_high and latest > or_high:
            lines.append("Opening range is already reclaimed; avoid late chase unless retest holds.")
        elif latest and or_low and latest < or_low:
            lines.append("Opening range floor is broken; avoid calls until reclaim.")
        elif structure.get("bias") == "balanced / tactical":
            lines.append("Auction is balanced; wait for sweep/reclaim instead of front-running direction.")
        return lines

    def _risk_flags(self, payload: dict[str, Any]) -> list[str]:
        flags: list[str] = []
        dealer = str(payload.get("dealer_gamma", {}).get("dealer_regime", ""))
        if "pin risk" in dealer:
            flags.append("Dealer regime warns of pin/mean-reversion; take profits faster unless expansion confirms.")
        if int(payload.get("high_impact_count", 0) or 0) > 0:
            flags.append("Market-relevant high-impact catalysts are active; expect headline whipsaws.")
        if payload.get("cross_confirmation", {}).get("state") == "unconfirmed":
            flags.append("SPY structure lacks index confirmation; reduce conviction.")
        rsi = self._safe_float(payload.get("rsi_5m"), 50.0)
        if rsi > 72:
            flags.append("RSI is extended; wait for reset or failed-break signal.")
        if rsi < 35:
            flags.append("RSI is washed out; puts need continuation, not late chase.")
        return flags or ["No major desk risk flag beyond normal 0DTE gamma risk."]

    def format_report(self, payload: dict[str, Any], title: str) -> str:
        structure = payload.get("structure", {})
        zones = payload.get("zones", {})
        cross = payload.get("cross_confirmation", {})
        confidence = payload.get("confidence", {})
        dealer = payload.get("dealer_gamma", {})
        sentiment = payload.get("sentiment", {}) or {}
        lines = [
            f"<b>{escape(title)}</b>",
            f"<i>{escape(str(payload.get('timestamp', '')))}</i>",
            "",
            "<b>DESK READ</b>",
            f"• Bias: {escape(self._desk_bias(payload))}",
            f"• Grade: {escape(str(confidence.get('grade', 'n/a')))} | Score: {escape(str(confidence.get('score', 0)))} / 100",
            f"• Structure: {escape(str(structure.get('bias', 'balanced / tactical')))} | {escape(str(structure.get('day_type', 'rotation / mean-reversion structure')))}",
            f"• Trend vs Mean Reversion: {escape(str(confidence.get('trend_probability', 50)))}% / {escape(str(confidence.get('mean_reversion_probability', 50)))}%",
            f"• Dealer Regime: {escape(str(dealer.get('dealer_regime', 'unknown')))} | Exposure: {escape(str(dealer.get('exposure_score', 0)))}",
            f"• Cross Check: {escape(str(cross.get('state', 'n/a')))} | Confirmations: {escape(str(cross.get('confirmations', 0)))}",
            "",
            "<b>KEY LEVELS</b>",
            f"• SPY: {self._price(payload.get('latest'))} | XSP: {self._price(payload.get('xsp_latest'))} ({escape(str(payload.get('xsp_symbol_used') or 'n/a'))}) | SPX: {self._price(payload.get('spx_latest'))} ({escape(str(payload.get('spx_symbol_used') or 'n/a'))})",
            f"• VWAP: {self._price(payload.get('vwap'))}",
            f"• Premarket High/Low: {self._price(payload.get('premarket_high'))} / {self._price(payload.get('premarket_low'))}",
            f"• Opening Range Ceiling/Floor: {self._price(payload.get('opening_range_high'))} / {self._price(payload.get('opening_range_low'))}",
            f"• Gamma Pin/Flip: {escape(str(zones.get('pin', 'n/a')))} / {escape(str(zones.get('flip', 'n/a')))}",
            f"• Gamma Support/Resistance: {escape(str(zones.get('support', 'n/a')))} / {escape(str(zones.get('resistance', 'n/a')))}",
            "",
            "<b>EXECUTION PLAN</b>",
        ]
        lines.extend(f"• {escape(item)}" for item in self._execution_plan(payload))
        lines.extend(["", "<b>INVALIDATION / RISK FLAGS</b>"])
        lines.extend(f"• {escape(item)}" for item in self._risk_flags(payload))
        lines.extend([
            "",
            "<b>ORB / VWAP / RSI</b>",
            f"• Opening Drive: {escape(str(payload.get('opening_drive', 'n/a')))}",
            f"• Volatility State: {escape(str(payload.get('volatility_state', 'unknown')))}",
            f"• 5m RSI: {escape(str(payload.get('rsi_5m')))} | Daily RSI: {escape(str(payload.get('rsi_daily')))}",
        ])
        lines.extend(["", "<b>VOLUME PROFILE / LIQUIDITY</b>"])
        lines.extend(f"• {escape(str(item))}" for item in payload.get("volume_nodes", [])[:4])
        lines.extend(["", "<b>LIQUIDITY SWEEP NOTES</b>"])
        lines.extend(f"• {escape(str(item))}" for item in payload.get("sweep_notes", [])[:4])
        lines.extend(["", "<b>DEALER / GAMMA NOTES</b>"])
        lines.extend(f"• {escape(str(item))}" for item in dealer.get("notes", [])[:4])
        lines.extend(["", "<b>CROSS-CHECK NOTES</b>"])
        lines.extend(f"• {escape(str(item))}" for item in cross.get("notes", [])[:4])
        lines.extend(["", "<b>CONFIDENCE NOTES</b>"])
        lines.extend(f"• {escape(str(item))}" for item in confidence.get("notes", [])[:6])
        lines.extend([
            "",
            "<b>MACRO / SENTIMENT</b>",
            f"• Institutional Tone: {escape(str(sentiment.get('sentiment', 'neutral')))} ({sentiment.get('score', 0)})",
            f"• Headlines: {payload.get('headline_count')} | Market Events: {payload.get('market_event_count', 0)} / Raw Events: {payload.get('raw_event_count', 0)} | High-Impact Market Events: {payload.get('high_impact_count')}",
        ])
        for event in payload.get("events", [])[:4]:
            lines.append(f"• {escape(str(event))}")
        if payload.get("top_headlines"):
            lines.extend(["", "<b>TOP MARKET HEADLINES</b>"])
            lines.extend(f"• {escape(str(item))}" for item in payload.get("top_headlines", [])[:4])
        lines.extend(["", "<b>FINAL DESK NOTE</b>"])
        lines.append("• Trade the confirmation, not the first impulse. In 0DTE, a clean no-trade is better than forcing chop.")
        return "\n".join(lines)

    async def run_breakdown(self) -> dict[str, Any]:
        payload = await self.analyze()
        await self.telegram_app.bot.send_message(chat_id=self.chat_id, text=self.format_report(payload, "🧭 6:15 AM SPY/XSP 0DTE Direction Desk"), parse_mode="HTML")
        return payload

    async def run_midday(self) -> dict[str, Any]:
        payload = await self.analyze()
        await self.telegram_app.bot.send_message(chat_id=self.chat_id, text=self.format_report(payload, "☀️ 10:00 AM ET SPY/XSP 0DTE Midday Desk"), parse_mode="HTML")
        return payload
