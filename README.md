# Aggressive Portfolio Bot

Production async trading assistant with Telegram control, SQLite persistence, Polygon and Finnhub market data, Alpaca stock execution, Tradier options execution, and optional Google Sheets ledger export.

## Runtime
- `app.py` boots settings, logging, SQLite, data clients, broker clients, scanner services, Telegram handlers, and scheduled jobs.
- Telegram is the control surface for scans, presets, filters, execution mode, strategies, ticker research, options chain tools, trailing stops, and SPY/XSP 0DTE reports.
- SQLite is the source of truth for persistent settings and bot state.
- Google Sheets export is optional and must not stop startup if the sheet is unavailable.

## Scheduled reports
Schedules are evaluated in `APP_TIMEZONE`.

Recommended deployment timezone:

```text
APP_TIMEZONE=America/Los_Angeles
```

Current market workflow:
- 5:30 AM Pacific: premarket scan
- 6:15 AM Pacific: SPY/XSP 0DTE direction desk
- 7:00 AM Pacific / 10:00 AM Eastern: SPY/XSP 0DTE midday desk
- 9:00 PM Pacific: postmarket / overnight prep
- Sunday 9:00 PM Pacific: weekly wrap / Monday prep

## SPY/XSP 0DTE intelligence layer
`services/spy_0dte_service.py` is the shared analysis layer for the 6:15 AM and 10:00 AM ET reports. It is analysis-only and does not place orders.

Current report inputs include:
- Polygon SPY minute and daily bars
- VWAP
- RSI
- opening range ceiling/floor
- premarket high/low
- option-chain concentration zones from Tradier when available
- volume profile nodes
- range/sweep notes
- volatility-state classification
- Finnhub market news sentiment
- Finnhub economic calendar events

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
- `ENABLE_DEMO_POSITION_FALLBACK=false`
- Live trading should not be enabled by default.
