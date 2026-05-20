from __future__ import annotations

import logging

from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
)

from .admin_handlers import build_admin_handlers
from .analytics_handlers import build_analytics_handlers
from .execution_handlers import build_execution_handlers
from .handler_registry import dedupe_handlers, summarize_handlers
from .runtime_handlers import build_runtime_handlers
from .spy_0dte_handlers import build_spy_0dte_handlers
from .spy_calibration_handlers import build_spy_calibration_handlers
from .spy_dashboard_handlers import build_spy_dashboard_handlers
from .spy_learning_handlers import build_spy_learning_handlers
from .spy_performance_handlers import build_spy_performance_handlers

# PANEL CALLBACK ROUTER
from .panel_callbacks import handle_panel_callback

logger = logging.getLogger(
    "aggressive_portfolio_bot.telegram.bot"
)


def build_telegram_app(
    token: str,
    app_services,
    config_service,
    admin_chat_id: int,
):
    app = ApplicationBuilder().token(token).build()

    handlers = dedupe_handlers([
        build_runtime_handlers(
            app_services,
            admin_chat_id,
        ),

        build_admin_handlers(
            app_services,
            config_service,
            admin_chat_id,
        ),

        build_spy_0dte_handlers(
            app_services,
            admin_chat_id,
        ),

        build_spy_performance_handlers(
            app_services,
            admin_chat_id,
        ),

        build_spy_calibration_handlers(
            app_services,
            admin_chat_id,
        ),

        build_spy_dashboard_handlers(
            app_services,
            admin_chat_id,
        ),

        build_spy_learning_handlers(
            app_services,
            admin_chat_id,
        ),

        build_execution_handlers(
            app_services,
            config_service,
            admin_chat_id,
        ),

        build_analytics_handlers(
            app_services,
            config_service,
            admin_chat_id,
        ),
    ])

    # COMMAND HANDLERS
    for handler in handlers:
        app.add_handler(handler)

    # CONTROL PANEL CALLBACKS
    app.add_handler(
        CallbackQueryHandler(
            handle_panel_callback,
            pattern=(
                r"^(cp|scan|exec|ml|preset|presetprofile|"
                r"profilefilters|fcat|fedit|freset|"
                r"fopt|foptedit|foptchoice|foptset|"
                r"execedit|execchoice|execset|"
                r"set|toggle)\|"
            ),
        )
    )

    summary = summarize_handlers(handlers)

    logger.info(
        "Registered Telegram handlers: "
        "handler_count=%s "
        "command_count=%s "
        "commands=%s",
        summary["handler_count"],
        summary["command_count"],
        summary["commands"],
    )

    app.bot_data["handler_summary"] = summary

    return app
