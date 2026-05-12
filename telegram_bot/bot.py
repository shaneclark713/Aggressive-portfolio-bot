from __future__ import annotations

from telegram.ext import ApplicationBuilder

from .handlers import build_handlers
from .spy_0dte_handlers import build_spy_0dte_handlers


def build_telegram_app(token: str, app_services, config_service, admin_chat_id: int):
    app = ApplicationBuilder().token(token).build()
    for handler in build_handlers(app_services, config_service, admin_chat_id):
        app.add_handler(handler)
    for handler in build_spy_0dte_handlers(app_services, admin_chat_id):
        app.add_handler(handler)
    return app
