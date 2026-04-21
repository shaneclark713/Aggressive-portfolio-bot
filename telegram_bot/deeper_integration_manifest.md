# Deeper Integration Bundle

This bundle continues the Telegram/UI execution build with the next set of new files.

## New files included
- services/options_chain_service.py
- execution/ladder_manager.py
- execution/trailing_manager.py
- execution/multi_leg.py
- services/options_order_service.py

## What these support
- real options chain normalization and summaries
- laddered entries
- laddered exits
- trailing stop tracking
- multi-leg option order payloads
- vertical spread scaffolding

## Next existing files to update after this bundle
- telegram_bot/handlers.py
- telegram_bot/keyboards.py
- telegram_bot/formatters.py
- brokers/tradier.py
- brokers/execution_router.py
