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
    "telegram_bot.admin_handlers",
    "telegram_bot.analytics_handlers",
    "telegram_bot.bot",
    "telegram_bot.execution_handlers",
    "telegram_bot.handler_registry",
    "telegram_bot.handlers",
    "telegram_bot.runtime_handlers",
    "telegram_bot.spy_0dte_handlers",
    "telegram_bot.ui_helpers",
]

# remaining file unchanged
