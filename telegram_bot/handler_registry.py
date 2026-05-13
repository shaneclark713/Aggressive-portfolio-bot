from __future__ import annotations

import logging
from collections.abc import Iterable
from typing import Any

from telegram.ext import CommandHandler

logger = logging.getLogger("aggressive_portfolio_bot.telegram.handler_registry")


def command_names(handler: Any) -> list[str]:
    """Return command names exposed by a Telegram CommandHandler."""
    if not isinstance(handler, CommandHandler):
        return []
    commands = getattr(handler, "commands", None) or []
    return sorted(str(command).lstrip("/") for command in commands)


def dedupe_handlers(handler_groups: Iterable[Iterable[Any]]) -> list[Any]:
    """Flatten Telegram handler groups and skip duplicate CommandHandlers.

    First registration wins. This keeps newer focused modules, such as SPY/XSP
    handlers, from being shadowed by older legacy handlers if a command name is
    accidentally registered twice.
    """
    seen_commands: set[str] = set()
    handlers: list[Any] = []
    for group in handler_groups:
        for handler in group:
            names = command_names(handler)
            duplicate_names = [name for name in names if name in seen_commands]
            if duplicate_names:
                logger.warning("Skipping duplicate Telegram command handler(s): %s", duplicate_names)
                continue
            seen_commands.update(names)
            handlers.append(handler)
    return handlers


def summarize_handlers(handlers: Iterable[Any]) -> dict[str, Any]:
    command_list: list[str] = []
    handler_count = 0
    for handler in handlers:
        handler_count += 1
        command_list.extend(command_names(handler))
    return {
        "handler_count": handler_count,
        "command_count": len(command_list),
        "commands": sorted(command_list),
    }
