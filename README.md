# Aggressive Portfolio Bot

Production async trading assistant with Telegram control, SQLite persistence, Polygon and Finnhub market data, Alpaca stock execution, Tradier options execution, and optional Google Sheets ledger export.

## Runtime
- `app.py` boots settings, logging, SQLite, data clients, broker clients, scanner services, Telegram handlers, and scheduled jobs.
- Telegram is the control surface for scans, presets, filters, execution mode, strategies, ticker research, options chain tools, and trailing stops.
- SQLite is the source of truth for persistent settings and bot state.
- Google Sheets export is optional and must not stop startup if the sheet is unavailable.

## Execution modes
- `alerts_only`: default safe mode. No broker orders are submitted.
- `paper`: routes orders to paper or sandbox broker credentials only.
- `live`: routes orders to live broker credentials.

## Broker stack
- Stocks and equities: Alpaca
- Options: Tradier
- Market data: Polygon and Finnhub

## Render deployment
Use the keys defined in `.env.example` and `docs/RENDER_ENV_VARS.md`.

Recommended persistent database path:

```text
BOT_STORAGE_PATH=/var/data/bot.db
```

## Telegram admin lock
Only `TELEGRAM_ADMIN_CHAT_ID` is allowed to control the bot.

## Default safety posture
- `BOT_DEFAULT_EXECUTION_MODE=alerts_only`
- `BROKER_ENABLED=false`
- Live trading should not be enabled by default.
