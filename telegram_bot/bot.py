from __future__ import annotations

import logging

from telegram.ext import ApplicationBuilder

from .execution_handlers import build_execution_handlers
from .handler_registry import dedupe_handlers, summarize_handlers
from .handlers import build_handlers
from .runtime_handlers import build_runtime_handlers
from .spy_0dte_handlers import build_spy_0dte_handlers

logger = logging.getLogger("aggressive_portfolio_bot.telegram.bot")


def build_telegram_app(token: str, app_services, config_service, admin_chat_id: int):
    app = ApplicationBuilder().token(token).build()
    handlers = dedupe_handlers([
        build_runtime_handlers(app_services, admin_chat_id),
        build_spy_0dte_handlers(app_services, admin_chat_id),
        build_execution_handlers(app_services, config_service, admin_chat_id),
        build_handlers(app_services, config_service, admin_chat_id),
    ])
    for handler in handlers:
        app.add_handler(handler)
    summary = summarize_handlers(handlers)
    logger.info(
        "Registered Telegram handlers: handler_count=%s command_count=%s commands=%s",
        summary["handler_count"],
        summary["command_count"],
        summary["commands"],
    )
    app.bot_data["handler_summary"] = summary
    return app
