from __future__ import annotations

import json
import logging
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping

logger = logging.getLogger("aggressive_portfolio_bot.services.ticker_research")


class TickerResearchService:
    """One-symbol research and scan-history storage.

    This service intentionally does not depend on the universe/discovery passers list.
    It can research a ticker directly, save a compact scan record, and return recent
    history for Telegram display.
    """

    VALID_SCAN_TYPES = {"market", "premarket", "midday", "overnight", "catalyst"}
    SCAN_ALIASES = {
        "day": "market",
        "day_trade": "market",
        "overall": "market",
        "scan": "market",
        "swing": "overnight",
        "swing_trade": "overnight",
        "news": "catalyst",
        "research": "market",
    }

    def __init__(
        self,
        storage_path: str | Path,
        scanner=None,
        market_client=None,
        news_client=None,
        options_chain_ingest=None,
        chain_service=None,
        iv_analyzer=None,
        flow_analyzer=None,
    ):
        base_path = Path(storage_path)
        storage_root = base_path if base_path.suffix == "" else base_path.parent
        self.history_dir = storage_root / "ticker_research"
        self.history_path = self.history_dir / "history.json"
        self.scanner = scanner
        self.market_client = market_client or getattr(scanner, "market_client", None)
        self.news_client = news_client or getattr(scanner, "news_client", None)
        self.options_chain_ingest = options_chain_ingest
        self.chain_service = chain_service
        self.iv_analyzer = iv_analyzer
        self.flow_analyzer = flow_analyzer
        self.history_dir.mkdir(parents=True, exist_ok=True)

    def normalize_scan_type(self, scan_type: str | None) -> str:
        value = str(scan_type or "market").strip().lower()
        value = self.SCAN_ALIASES.get(value, value)
        return value if value in self.VALID_SCAN_TYPES else "market"

    def _load_history(self) -> list[dict[str, Any]]:
        if not self.history_path.exists():
            return []
        try:
            payload = json.loads(self.history_path.read_text(encoding="utf-8"))
            if isinstance(payload, list):
                return payload
        except Exception as exc:
            logger.warning("Could not load ticker research history: %s", exc)
        return []

    def _save_history(self, rows: list[dict[str, Any]]) -> None:
        rows = rows[-500:]
        tmp_path = self.history_path.with_suffix(".tmp")
        tmp_path.write_text(json.dumps(rows, indent=2, sort_keys=True), encoding="utf-8")
        tmp_path.replace(self.history_path)

    def save_record(self, record: Mapping[str, Any]) -> None:
        rows = self._load_history()
        rows.append(dict(record))
        self._save_history(rows)

    def list_history(self, symbol: str | None = None, limit: int = 10) -> list[dict[str, Any]]:
        limit = max(1, min(int(limit or 10), 50))
        symbol = str(symbol or "").strip().upper()
        rows = self._load_history()
        if symbol:
            rows = [row for row in rows if str(row.get("symbol", "")).upper() == symbol]
        return list(reversed(rows[-limit:]))

    def clear_history(self, symbol: str | None = None) -> int:
        rows = self._load_history()
        if not symbol:
            removed = len(rows)
            self._save_history([])
            return removed
        symbol = str(symbol).strip().upper()
        kept = [row for row in rows if str(row.get("symbol", "")).upper() != symbol]
        removed = len(rows) - len(kept)
        self._save_history(kept)
        return removed

    async def _fetch_daily_context(self, symbol: str) -> dict[str, Any]:
        if self.market_client is None:
            return {"available": False, "error": "market_client_unavailable"}
        out: dict[str, Any] = {"available": False}
        try:
            df = await self.market_client.get_historical_data(symbol=symbol, multiplier=1, timespan="day")
        except Exception as exc:
            return {"available": False, "error": f"daily_data_error: {self._compact_error(exc)}"}
        if df is None or df.empty:
            return {"available": False, "error": "empty_daily_data"}
        work = df[[column for column in ["open", "high", "low", "close", "volume"] if column in df.columns]].dropna().copy()
        if work.empty:
            return {"available": False, "error": "empty_clean_daily_data"}
        latest = work.iloc[-1]
        close = float(latest.get("close", 0) or 0)
        volume = float(latest.get("volume", 0) or 0)
        avg_volume_20 = float(work["volume"].tail(20).mean()) if "volume" in work.columns else 0.0
        relative_volume = float(volume / avg_volume_20) if avg_volume_20 else 0.0
        sma20 = float(work["close"].tail(20).mean()) if len(work) >= 20 else None
        sma50 = float(work["close"].tail(50).mean()) if len(work) >= 50 else None
        prior_close = float(work["close"].iloc[-2]) if len(work) >= 2 else close
        change_pct = ((close - prior_close) / prior_close) if prior_close else 0.0
        atr_pct = None
        if len(work) >= 15:
            high_low = work["high"] - work["low"]
            high_close = (work["high"] - work["close"].shift(1)).abs()
            low_close = (work["low"] - work["close"].shift(1)).abs()
            atr = max(high_low.tail(14).mean(), high_close.tail(14).mean(), low_close.tail(14).mean())
            atr_pct = float(atr / close) if close else 0.0
        trend = "neutral"
        if sma20 and sma50:
            if close > sma20 > sma50:
                trend = "bullish"
            elif close < sma20 < sma50:
                trend = "bearish"
        out.update(
            {
                "available": True,
                "last_close": close,
                "latest_volume": volume,
                "avg_volume_20": avg_volume_20,
                "relative_volume": relative_volume,
                "sma20": sma20,
                "sma50": sma50,
                "change_pct": change_pct,
                "atr_pct": atr_pct,
                "trend": trend,
                "bars_loaded": int(len(work)),
            }
        )
        return out

    async def _fetch_news_context(self, symbol: str, limit: int = 5) -> dict[str, Any]:
        if self.news_client is None:
            return {"news_count": 0, "headlines": [], "error": "news_client_unavailable"}
        today = date.today().isoformat()
        start = (date.today() - timedelta(days=7)).isoformat()
        try:
            rows = await self.news_client.fetch_ticker_news(symbol, start_date=start, end_date=today)
            headlines = self.news_client.summarize_headlines(rows, limit=limit)
            return {"news_count": len(rows), "headlines": headlines}
        except Exception as exc:
            return {"news_count": 0, "headlines": [], "error": f"news_error: {self._compact_error(exc)}"}

    async def _fetch_options_context(self, symbol: str, include_options: bool = True) -> dict[str, Any]:
        if not include_options:
            return {"enabled": False}
        if self.options_chain_ingest is None:
            return {"enabled": False, "error": "options_chain_service_unavailable"}
        try:
            payload = await self.options_chain_ingest.refresh_chain(symbol)
            rows = list(payload.get("rows", []))
            summary = dict(payload.get("summary", {}))
            iv_summary = self.iv_analyzer.summarize_chain(rows) if self.iv_analyzer else {}
            flow_summary = self.flow_analyzer.summarize(rows) if self.flow_analyzer else {}
            return {
                "enabled": True,
                "summary": summary,
                "iv": iv_summary,
                "flow": flow_summary,
            }
        except Exception as exc:
            return {"enabled": True, "error": f"options_error: {self._compact_error(exc)}"}

    def _compact_error(self, exc: Exception) -> str:
        text = str(exc).lower()
        if "429" in text or "rate_limited" in text or "too many requests" in text:
            return "rate_limited"
        if "timeout" in text:
            return "timeout"
        return exc.__class__.__name__

    def _compact_record(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        scan = dict(payload.get("scan") or {})
        daily = dict(payload.get("daily") or {})
        options = dict(payload.get("options") or {})
        option_summary = dict(options.get("summary") or {})
        return {
            "created_at": payload.get("created_at"),
            "symbol": payload.get("symbol"),
            "scan_type": payload.get("scan_type"),
            "status": payload.get("status"),
            "qualified": scan.get("qualified"),
            "passed_filters": scan.get("passed_filters"),
            "strategy_signal": scan.get("strategy_signal"),
            "reason": payload.get("reason") or scan.get("rejection_reason") or scan.get("error"),
            "price": daily.get("last_close") or scan.get("price"),
            "relative_volume": daily.get("relative_volume") or scan.get("relative_volume"),
            "trend": daily.get("trend"),
            "news_count": (payload.get("news") or {}).get("news_count"),
            "option_contracts": option_summary.get("contract_count", 0),
            "option_flow_bias": (options.get("flow") or {}).get("bias"),
        }

    async def research_ticker(self, symbol: str, scan_type: str = "market", include_options: bool = True) -> dict[str, Any]:
        symbol = str(symbol or "").strip().upper()
        scan_type = self.normalize_scan_type(scan_type)
        created_at = datetime.now(timezone.utc).isoformat()
        payload: dict[str, Any] = {
            "symbol": symbol,
            "scan_type": scan_type,
            "created_at": created_at,
            "status": "ERROR",
            "reason": None,
            "scan": {},
            "daily": {},
            "news": {},
            "options": {},
        }
        if not symbol:
            payload["reason"] = "missing_symbol"
            return payload

        if self.scanner is not None:
            try:
                payload["scan"] = await self.scanner.scan_ticker_overview(symbol, scan_type=scan_type)
            except Exception as exc:
                payload["scan"] = {"symbol": symbol, "scan_type": scan_type, "error": f"scan_error: {self._compact_error(exc)}"}
        else:
            payload["scan"] = {"symbol": symbol, "scan_type": scan_type, "error": "scanner_unavailable"}

        payload["daily"] = await self._fetch_daily_context(symbol)
        payload["news"] = await self._fetch_news_context(symbol)
        payload["options"] = await self._fetch_options_context(symbol, include_options=include_options)

        scan = payload["scan"]
        options_summary = (payload["options"] or {}).get("summary") or {}
        if scan.get("qualified"):
            payload["status"] = "QUALIFIED"
        elif scan.get("passed_filters"):
            payload["status"] = "WATCHLIST"
        elif options_summary.get("contract_count", 0):
            payload["status"] = "OPTIONS_DATA"
        elif payload["daily"].get("available") or payload["news"].get("news_count", 0):
            payload["status"] = "DATA_ONLY"
        else:
            payload["status"] = "ERROR"
            payload["reason"] = scan.get("error") or payload["daily"].get("error") or "no_data_available"

        if payload["reason"] is None:
            payload["reason"] = scan.get("rejection_reason") or scan.get("error")

        self.save_record(self._compact_record(payload))
        return payload
