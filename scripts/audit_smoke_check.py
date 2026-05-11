from __future__ import annotations

import importlib
import sys
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
    "services.position_sync_service",
    "services.spy_0dte_service",
    "telegram_bot.bot",
    "telegram_bot.handlers",
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


def main() -> int:
    checks = {
        "imports": _check_imports,
        "schedules": _check_schedules,
        "order_request": _check_order_request,
        "demo_fallback_guard": _check_demo_fallback_guard,
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
