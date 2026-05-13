from __future__ import annotations

import json
import logging
from typing import Any

from telegram.error import BadRequest

logger = logging.getLogger("aggressive_portfolio_bot.telegram.ui_helpers")

PENDING_FILTER_EDIT = "pending_filter_edit"
PENDING_EXEC_EDIT = "pending_execution_edit"
PENDING_OPTIONS_EDIT = "pending_options_edit"
PENDING_TICKER_SCAN = "pending_ticker_scan"
PENDING_TICKER_RESEARCH = "pending_ticker_research"
PENDING_KEYS = (
    PENDING_FILTER_EDIT,
    PENDING_EXEC_EDIT,
    PENDING_OPTIONS_EDIT,
    PENDING_TICKER_SCAN,
    PENDING_TICKER_RESEARCH,
)


def meta_key(name: str) -> str:
    return f"__meta__.ui.{name}"


def parse_meta_value(raw: Any) -> dict[str, Any]:
    if raw is None:
        return {}
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}
    return {}


def get_ui_settings(settings_repo, name: str, default: dict | None = None) -> dict[str, Any]:
    default = dict(default or {})
    try:
        overrides = settings_repo.get_filter_overrides()
        parsed = parse_meta_value(overrides.get(meta_key(name)))
        merged = dict(default)
        merged.update(parsed)
        return merged
    except Exception as exc:
        logger.warning("Failed to read UI settings %s: %s", name, exc)
        return default


def set_ui_settings(settings_repo, name: str, payload: dict[str, Any]) -> dict[str, Any]:
    settings_repo.set_filter_override(meta_key(name), json.dumps(payload))
    return payload


def clear_pending_user_state(context) -> None:
    for key in PENDING_KEYS:
        context.user_data.pop(key, None)


def clean_number(raw: str) -> str:
    return str(raw).strip().replace(",", "")


def parse_bool(raw: str) -> bool:
    lowered = str(raw).strip().lower()
    if lowered in {"true", "1", "yes", "on", "enabled"}:
        return True
    if lowered in {"false", "0", "no", "off", "disabled"}:
        return False
    raise ValueError("Expected true/false")


def parse_decimal_or_percent(raw: str) -> float:
    text = clean_number(raw)
    if text.endswith("%"):
        return float(text[:-1]) / 100.0
    value = float(text)
    if abs(value) > 1.0:
        return value / 100.0
    return value


async def safe_edit_message_text(query, text: str, **kwargs):
    try:
        return await query.edit_message_text(text, **kwargs)
    except BadRequest as exc:
        if "Message is not modified" in str(exc):
            return None
        logger.warning("Telegram edit_message_text failed: %s", exc)
        raise


async def authorize_update(update, admin_chat_id: int) -> bool:
    chat_id = update.effective_chat.id if update.effective_chat else None
    if chat_id == admin_chat_id:
        return True
    target = update.message or getattr(update, "callback_query", None)
    if target is not None:
        if hasattr(target, "reply_text"):
            await target.reply_text("Unauthorized.")
        elif hasattr(target, "answer"):
            await target.answer("Unauthorized", show_alert=True)
    return False
