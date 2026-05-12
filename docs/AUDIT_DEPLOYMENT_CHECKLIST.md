# Audit Deployment Checklist

Use this checklist after merging the audit branch and before manually redeploying Render.

## Branch

```text
audit/phase-1-runtime-blockers
```

## Render redeploy rule

Do not redeploy after every individual fix. Merge the completed audit branch, then run one controlled redeploy and fix any startup/runtime errors from that single pass.

## Render build/start settings

This repo does not currently use `render.yaml`, so Render settings are expected to live in the Render dashboard.

Recommended settings:

```text
Environment: Docker
Dockerfile: Dockerfile
Start command: inherited from Dockerfile
Docker CMD: python app.py
```

The Dockerfile already installs `requirements.txt` and starts:

```text
python app.py
```

## Required Render environment values

```text
APP_TIMEZONE=America/Los_Angeles
BOT_DEFAULT_EXECUTION_MODE=alerts_only
BROKER_ENABLED=false
ENABLE_DEMO_POSITION_FALLBACK=false
```

## Schedule expectations

Schedules are evaluated in `APP_TIMEZONE`.

```text
5:30 AM Pacific  -> premarket scan
6:15 AM Pacific  -> SPY/XSP 0DTE direction desk
7:00 AM Pacific  -> 10:00 AM Eastern SPY/XSP 0DTE midday desk
9:00 PM Pacific  -> postmarket / overnight prep
Sunday 9:00 PM Pacific -> Monday prep / weekly wrap
```

## Startup checks

After redeploy, confirm logs show:

```text
BOT_STORAGE_PATH=<expected persistent path>
Resolved persistent SQLite database file: <expected file>
Scheduler started
Telegram polling started
```

## Telegram checks

Run these from the admin chat only:

```text
/panel
/sync_positions
/trail_status
/scan_ticker SPY market
/research_ticker SPY market
/spy_0dte
/spy_midday
/spy_levels
/spy_gamma
```

Expected safety behavior:

- `/sync_positions` must not show `SPY-demo` or `QQQ-demo` unless `ENABLE_DEMO_POSITION_FALLBACK=true` is intentionally set.
- Execution mode should boot into `alerts_only`.
- Paper mode should not fall back to live broker credentials.
- Alerts-only mode should block all broker order submission.

## SPY/XSP desk checks

The 6:15 and 7:00 Pacific scheduled reports should include:

- SPY last price
- VWAP
- RSI
- premarket high/low
- opening range ceiling/floor
- opening-drive classification
- volatility state
- volume profile nodes
- sweep/range notes
- dealer/gamma regime and exposure score
- pin / flip / support / resistance zones when Tradier data is available
- SPY/XSP/SPX cross-confirmation when Polygon data is available
- confidence grade
- trend vs mean-reversion probability
- news sentiment
- economic calendar events

## Known optional data behavior

- XSP/SPX cross-confirmation is optional. If the market data provider does not return index symbols through the configured endpoint, the report should continue using SPY-only structure and show the cross-check as unavailable.
- Dealer/gamma zones depend on Tradier chain availability. If Tradier is not configured or returns no chain, the report should continue without crashing.

## Local smoke check before merge/redeploy

Run this before merging or redeploying if you have the repo locally:

```text
python scripts/audit_smoke_check.py
```

Expected output:

```text
AUDIT SMOKE CHECK PASSED
```

## Do not enable live mode until verified

Only move beyond `alerts_only` after:

1. Telegram admin lock works.
2. Paper mode order routing is verified.
3. Position sync matches broker state.
4. SPY/XSP report runs without exceptions.
5. Risk controls are confirmed.
6. You intentionally switch execution mode from Telegram.
