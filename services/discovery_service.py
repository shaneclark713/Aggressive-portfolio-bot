from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger("aggressive_portfolio_bot.services.discovery")


class DiscoveryService:
    PROFILE_MAP = {
        "market": "overall",
        "scan": "overall",
        "overall": "overall",
        "premarket": "premarket",
        "midday": "midday",
        "overnight": "overnight",
        "swing": "overnight",
    }

    def __init__(self, market_client, config_service, storage_path: Path):
        self.market_client = market_client
        self.config_service = config_service
        self.snapshot_dir = Path(storage_path) / "snapshot"
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)
        self._last_status: Dict[str, Dict[str, Any]] = {}

    def _profile_for_scan(self, scan_type: str) -> str:
        return self.PROFILE_MAP.get(scan_type, "overall")

    def _snapshot_path(self, profile: str) -> Path:
        return self.snapshot_dir / f"discovery_{profile}.json"

    def _max_age_minutes(self, profile: str) -> int:
        return {
            "premarket": 20,
            "midday": 45,
            "overnight": 180,
            "overall": 60,
        }.get(profile, 60)

    def _filters_for_profile(self, profile: str) -> Dict[str, Dict[str, Any]]:
        return self.config_service.resolve_filters(profile=profile)

    def _load_snapshot(self, profile: str) -> Dict[str, Any] | None:
        path = self._snapshot_path(profile)
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.warning("Failed to load snapshot %s: %s", profile, exc)
            return None

    def _save_snapshot(self, profile: str, payload: Dict[str, Any]) -> None:
        path = self._snapshot_path(profile)
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _is_stale(self, payload: Dict[str, Any] | None, profile: str) -> bool:
        if not payload:
            return True
        created = payload.get("created_at")
        if not created:
            return True
        try:
            created_dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
        except Exception:
            return True
        return datetime.now(timezone.utc) - created_dt > timedelta(minutes=self._max_age_minutes(profile))

    def _parse_snapshot_row(self, item: Dict[str, Any]) -> Dict[str, Any] | None:
        symbol = item.get("ticker") or item.get("symbol")
        if not symbol:
            return None

        day = item.get("day") or {}
        prev_day = item.get("prevDay") or {}
        last_trade = item.get("lastTrade") or {}
        last_quote = item.get("lastQuote") or {}

        price = last_trade.get("p") or day.get("c") or item.get("todaysChange") or prev_day.get("c")
        if price in (None, ""):
            return None

        try:
            price = float(price)
        except Exception:
            return None

        volume = float(day.get("v") or 0)
        prev_close = float(prev_day.get("c") or 0)
        day_open = float(day.get("o") or 0)
        day_high = float(day.get("h") or 0)
        day_low = float(day.get("l") or 0)
        todays_change_pct = item.get("todaysChangePerc")
        try:
            change_pct = float(todays_change_pct) if todays_change_pct is not None else 0.0
        except Exception:
            change_pct = 0.0
        if change_pct == 0.0 and prev_close:
            change_pct = ((price - prev_close) / prev_close) * 100.0

        gap_pct = 0.0
        if prev_close and day_open:
            gap_pct = abs((day_open - prev_close) / prev_close) * 100.0

        return {
            "symbol": symbol,
            "price": price,
            "day_volume": volume,
            "day_dollar_volume": price * volume,
            "change_pct": change_pct,
            "gap_pct": gap_pct,
            "prev_close": prev_close,
            "day_open": day_open,
            "day_high": day_high,
            "day_low": day_low,
            "bid": float(last_quote.get("P") or 0),
            "ask": float(last_quote.get("p") or 0),
        }

    async def build_snapshot(self, profile: str) -> Dict[str, Any]:
        raw = await self.market_client.get_full_market_snapshot()
        rows: List[Dict[str, Any]] = []
        skipped = 0
        for item in raw:
            parsed = self._parse_snapshot_row(item)
            if parsed is None:
                skipped += 1
                continue
            if parsed["price"] <= 0.25:
                skipped += 1
                continue
            if parsed["day_volume"] <= 0:
                skipped += 1
                continue
            rows.append(parsed)

        payload = {
            "profile": profile,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "row_count": len(rows),
            "skipped": skipped,
            "rows": rows,
        }
        self._save_snapshot(profile, payload)
        self._last_status[profile] = {
            "profile": profile,
            "created_at": payload["created_at"],
            "row_count": len(rows),
            "skipped": skipped,
            "source": "full_market_snapshot",
            "refresh_reason": "manual_or_stale",
        }
        logger.info("Built discovery snapshot for profile=%s rows=%s skipped=%s", profile, len(rows), skipped)
        return payload

    async def get_snapshot(self, profile: str, force_refresh: bool = False) -> Dict[str, Any]:
        payload = self._load_snapshot(profile)
        if force_refresh or self._is_stale(payload, profile):
            payload = await self.build_snapshot(profile)
        else:
            self._last_status[profile] = {
                "profile": profile,
                "created_at": payload.get("created_at"),
                "row_count": payload.get("row_count", len(payload.get("rows", []))),
                "skipped": payload.get("skipped", 0),
                "source": "cache",
                "refresh_reason": "fresh_cache",
            }
        return payload

    def filter_snapshot_rows(self, rows: List[Dict[str, Any]], profile: str, scan_type: str) -> List[Dict[str, Any]]:
        filters = self._filters_for_profile(profile)
        descriptive = filters["descriptive"]
        technical = filters["technical"]
        shortlist_cap = int(descriptive.get("shortlist_cap", 8) or 8)
        discovery_cap = max(shortlist_cap * 6, 30)

        min_price = float(descriptive.get("price_min", 0))
        min_day_volume = float(descriptive.get("avg_daily_volume_min", 0)) * 0.15
        min_dollar_volume = float(descriptive.get("avg_dollar_volume_min", 0)) * 0.15
        max_gap_pct = float(technical.get("premarket_gap_max_pct", 25.0))

        filtered: List[Dict[str, Any]] = []
        for row in rows:
            if row["price"] < min_price:
                continue
            if row["day_volume"] < min_day_volume:
                continue
            if row["day_dollar_volume"] < min_dollar_volume:
                continue
            if row["gap_pct"] > max_gap_pct:
                continue
            filtered.append(row)

        if scan_type == "premarket":
            filtered.sort(key=lambda x: (x["gap_pct"], x["day_dollar_volume"], abs(x["change_pct"])), reverse=True)
        elif scan_type == "midday":
            filtered.sort(key=lambda x: (x["day_dollar_volume"], abs(x["change_pct"])), reverse=True)
        elif scan_type == "overnight":
            filtered.sort(key=lambda x: (abs(x["change_pct"]), x["day_dollar_volume"]), reverse=True)
        else:
            filtered.sort(key=lambda x: (x["day_dollar_volume"], x["day_volume"]), reverse=True)

        return filtered[:discovery_cap]

    async def get_candidate_rows(self, scan_type: str, force_refresh: bool = False) -> List[Dict[str, Any]]:
        profile = self._profile_for_scan(scan_type)
        snapshot = await self.get_snapshot(profile, force_refresh=force_refresh)
        return self.filter_snapshot_rows(snapshot.get("rows", []), profile, scan_type)

    async def get_passing_symbols(self, scan_type: str, force_refresh: bool = False) -> List[str]:
        return [row["symbol"] for row in await self.get_candidate_rows(scan_type, force_refresh=force_refresh)]

    async def snapshot_status(self, profile: str | None = None) -> Dict[str, Any]:
        profile = profile or "overall"
        snapshot = await self.get_snapshot(profile, force_refresh=False)
        status = dict(self._last_status.get(profile, {}))
        status.setdefault("profile", profile)
        status.setdefault("created_at", snapshot.get("created_at"))
        status.setdefault("row_count", snapshot.get("row_count", len(snapshot.get("rows", []))))
        status.setdefault("skipped", snapshot.get("skipped", 0))
        return status
