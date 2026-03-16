# File Manifest

## Runtime
- `app.py`: application bootstrap, scheduler registration, dependency wiring
- `config/settings.py`: env-driven runtime configuration contract
- `database/*`: SQLite state, settings, alerts, trade records
- `services/*`: scheduled workflows and orchestration
- `telegram_bot/*`: commands, callbacks, control panel, formatters

## Data and strategy
- `data/*`: Polygon/Finnhub clients, universe filtering, scanners
- `strategies/*`: playbooks and router
- `risk/*`: kill switch, risk math, sizing

## Execution and accounting
- `brokers/*`: IBKR and Tradovate adapters plus execution router
- `ledger/*`: Google Sheets export
- `sandbox/*`: backtesting engine and helpers
