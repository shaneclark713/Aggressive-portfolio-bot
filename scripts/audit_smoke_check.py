from __future__ import annotations

import importlib
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

REQUIRED_MODULES = [
    "app",
    "brokers.models",
    "brokers.execution_router",
    "config.schedules",
    "core.scheduler",
    "database.spy_scan_repository",
    "services.dealer_gamma_service",
    "services.execution_guard_service",
    "services.position_sync_service",
    "services.risk_service",
    "services.spy_0dte_service",
    "services.spy_scan_journal_service",
    "services.spy_setup_score_service",
    "services.startup_recovery_service",
    "telegram_bot.bot",
    "telegram_bot.handler_registry",
    "telegram_bot.handlers",
    "telegram_bot.runtime_handlers",
    "telegram_bot.spy_0dte_handlers",
]


def _check_imports() -> list[str]:
    failures: list[str] = []
    for module_name in REQUIRED_MODULES:
        try:
            importlib.import_module(module_name)
        except Exception as exc:
            failures.append(f"{module_name}: {type(exc).__name__}: {exc}")
    return failures


def _check_schedules() -> list[str]:
    from config import schedules

    failures: list[str] = []
    expected = {
        "PREMARKET_SCHEDULE": (5, 30),
        "SPY_0DTE_BREAKDOWN_SCHEDULE": (6, 15),
        "MIDDAY_SCHEDULE": (7, 0),
        "POSTMARKET_SCHEDULE": (21, 0),
        "SUNDAY_WRAPUP_SCHEDULE": (21, 0),
    }
    for name, expected_time in expected.items():
        spec = getattr(schedules, name, None)
        actual = (getattr(spec, "hour", None), getattr(spec, "minute", None))
        if actual != expected_time:
            failures.append(f"{name}: expected {expected_time}, got {actual}")
    return failures


def _check_order_request() -> list[str]:
    from brokers.models import OrderRequest

    failures: list[str] = []
    order = OrderRequest(
        trade_id="smoke-test",
        broker="alpaca",
        symbol="spy",
        side="BUY",
        instrument_type="STOCK",
        quantity=1,
    )
    if order.symbol != "SPY":
        failures.append("OrderRequest did not normalize symbol to uppercase")
    if order.side != "buy":
        failures.append("OrderRequest did not normalize side to lowercase")
    if order.instrument_type != "stock":
        failures.append("OrderRequest did not normalize instrument_type to lowercase")
    return failures


def _check_demo_fallback_guard() -> list[str]:
    from services.position_sync_service import PositionSyncService

    failures: list[str] = []
    service = PositionSyncService(trailing_stop_service=None)
    if service._demo_fallback_enabled():
        failures.append("ENABLE_DEMO_POSITION_FALLBACK should default to false")
    return failures


def _check_dealer_gamma() -> list[str]:
    from services.dealer_gamma_service import DealerGammaService

    failures: list[str] = []
    service = DealerGammaService()
    rows = [
        {"strike": 500, "open_interest": 1000, "volume": 100, "option_type": "call", "gamma": 0.02},
        {"strike": 495, "open_interest": 800, "volume": 80, "option_type": "put", "gamma": 0.03},
        {"strike": 505, "open_interest": 700, "volume": 60, "option_type": "call", "gamma": 0.01},
    ]
    payload = service.summarize(500.0, rows).as_dict()
    for key in ("pin", "flip", "support", "resistance", "dealer_regime", "exposure_score", "notes"):
        if key not in payload:
            failures.append(f"Dealer gamma summary missing {key}")
    return failures


def _check_phase2_analytics() -> list[str]:
    from database.db import init_db
    from database.spy_scan_repository import SpyScanJournalRepository
    from services.spy_setup_score_service import SpySetupScoreService

    failures: list[str] = []
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    try:
        init_db(":memory:")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS spy_scan_journal (
                scan_id INTEGER PRIMARY KEY AUTOINCREMENT,
                scan_type TEXT NOT NULL,
                created_at TEXT NOT NULL,
                symbol TEXT NOT NULL DEFAULT 'SPY',
                latest REAL,
                structure_bias TEXT,
                structure_score INTEGER,
                confidence_grade TEXT,
                confidence_score INTEGER,
                trend_probability INTEGER,
                mean_reversion_probability INTEGER,
                dealer_regime TEXT,
                dealer_exposure_score INTEGER,
                payload TEXT NOT NULL,
                outcome TEXT,
                outcome_notes TEXT,
                outcome_marked_at TEXT
            )
        """)
        repo = SpyScanJournalRepository(conn)
        scan_id = repo.record_scan(
            "smoke",
            {
                "timestamp": "2026-01-01T09:30:00",
                "latest": 500.0,
                "structure": {"bias": "upside structure", "score": 50},
                "confidence": {"grade": "A", "score": 72, "trend_probability": 70, "mean_reversion_probability": 30},
                "dealer_gamma": {"dealer_regime": "hedge pressure", "exposure_score": 45},
            },
        )
        repo.mark_outcome(scan_id, "win", "smoke")
        accuracy = repo.accuracy_summary(limit=10)
        if accuracy.get("wins") != 1:
            failures.append("SPY scan repository did not record win outcome")
        scorer = SpySetupScoreService(repo)
        score = scorer.score_payload(
            {
                "structure": {"score": 50},
                "confidence": {"score": 72, "trend_probability": 70, "mean_reversion_probability": 30},
                "dealer_gamma": {"dealer_regime": "hedge pressure", "exposure_score": 45},
                "high_impact_count": 0,
                "data_quality": {},
            }
        )
        for key in ("score", "grade", "action", "reasons", "warnings", "calibration"):
            if key not in score:
                failures.append(f"SPY setup score missing {key}")
    finally:
        conn.close()
    return failures


class _FakeSettingsRepo:
    def __init__(self, profile: dict):
        self.profile = profile

    def normalize_execution_scope(self, scope: str) -> str:
        return scope

    def get_execution_settings(self, scope: str) -> dict:
        return dict(self.profile)


class _FakeTradeRepo:
    def get_consecutive_loss_count(self) -> int:
        return 2

    def get_recent_closed_trades(self, limit: int = 500):
        return [
            {"pnl": -150, "exit_time": datetime.now().isoformat()},
            {"pnl": -75, "exit_time": datetime.now().isoformat()},
        ]


def _check_phase3_execution_hardening() -> list[str]:
    from services.execution_guard_service import ExecutionGuardService
    from services.risk_service import RiskService

    failures: list[str] = []
    guard = ExecutionGuardService(default_cooldown_seconds=60)
    insufficient = guard.classify_failure("insufficient buying power")
    if insufficient.get("failure_type") != "insufficient_funds" or insufficient.get("is_retryable"):
        failures.append("ExecutionGuardService failed insufficient funds classification")
    transient = guard.classify_failure("timeout 503 connection error")
    if transient.get("failure_type") != "transient_api" or not transient.get("is_retryable"):
        failures.append("ExecutionGuardService failed transient API classification")
    key = guard.build_key({"symbol": "SPY", "side": "buy", "qty": 1, "type": "option"}, namespace="smoke")
    with guard.guarded(key, payload={"symbol": "SPY"}) as (allowed, reason):
        if not allowed or reason:
            failures.append("ExecutionGuardService blocked first guarded execution unexpectedly")
    allowed_after, reason_after = guard.check(key, cooldown_seconds=60)
    if allowed_after or not reason_after:
        failures.append("ExecutionGuardService did not enforce duplicate cooldown")

    risk = RiskService(
        _FakeSettingsRepo({
            "max_consecutive_losses": 2,
            "max_daily_loss": 100,
            "market_hours_only": False,
        }),
        _FakeTradeRepo(),
    )
    allowed, reason = risk.can_open_new_position(trade_style="day_trade")
    if allowed or not reason:
        failures.append("RiskService did not block after max loss/daily loss threshold")
    status = risk.status(trade_style="day_trade")
    for key_name in ("can_open_new_position", "blocked_reason", "daily_realized_pnl", "max_daily_loss"):
        if key_name not in status:
            failures.append(f"RiskService status missing {key_name}")
    return failures


def _check_phase4_telegram_registry() -> list[str]:
    from telegram.ext import CommandHandler
    from telegram_bot.handler_registry import command_names, dedupe_handlers, summarize_handlers

    async def noop(update, context):
        return None

    failures: list[str] = []
    one = CommandHandler("duplicate", noop)
    two = CommandHandler("duplicate", noop)
    unique = CommandHandler("unique", noop)
    handlers = dedupe_handlers([[one, two], [unique]])
    summary = summarize_handlers(handlers)
    if len(handlers) != 2:
        failures.append("handler registry did not dedupe duplicate commands")
    if command_names(one) != ["duplicate"]:
        failures.append("handler registry did not read command names")
    if "duplicate" not in summary.get("commands", []) or "unique" not in summary.get("commands", []):
        failures.append("handler registry summary missing expected commands")
    return failures


def main() -> int:
    checks = {
        "imports": _check_imports,
        "schedules": _check_schedules,
        "order_request": _check_order_request,
        "demo_fallback_guard": _check_demo_fallback_guard,
        "dealer_gamma": _check_dealer_gamma,
        "phase2_analytics": _check_phase2_analytics,
        "phase3_execution_hardening": _check_phase3_execution_hardening,
        "phase4_telegram_registry": _check_phase4_telegram_registry,
    }
    failures: list[str] = []
    for name, check in checks.items():
        result = check()
        if result:
            failures.extend(f"[{name}] {item}" for item in result)

    if failures:
        print("AUDIT SMOKE CHECK FAILED")
        for item in failures:
            print(f"- {item}")
        return 1

    print("AUDIT SMOKE CHECK PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
