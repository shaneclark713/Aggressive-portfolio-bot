# File Manifest

## Runtime
- `app.py`: application bootstrap, scheduler registration, dependency wiring
- `config/settings.py`: env-driven runtime configuration contract
- `config/logging_config.py`: Render/persistent-disk logging setup
- `database/*`: SQLite state, settings, alerts, trade records
- `services/*`: scheduled workflows, scans, research, options chain, risk, alerts, and execution orchestration
- `telegram_bot/*`: commands, callbacks, control panel, keyboards, and formatters

## Data and strategy
- `data/*`: Polygon/Finnhub clients, discovery, universe filtering, and scanners
- `strategies/*`: strategy playbooks and router
- `risk/*`: kill switch, risk math, and position sizing

## Execution and accounting
- `brokers/*`: Alpaca and Tradier adapters plus mode-aware execution router
- `execution/*`: ladder, multi-leg, safeguard, and trailing-position helpers
- `ledger/*`: optional Google Sheets export; failures must not stop bot startup

## Removed from production runtime
- `sandbox/*`: removed because backtesting skeletons were not wired into the live bot
