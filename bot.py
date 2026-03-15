from telegram.ext import ApplicationBuilder
from .handlers import build_handlers

def build_telegram_app(token:str, app_services, config_service, admin_chat_id:int):
    app=ApplicationBuilder().token(token).build()
    for handler in build_handlers(app_services, config_service, admin_chat_id): app.add_handler(handler)
    return app
