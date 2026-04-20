from __future__ import annotations

CORE_FUTURES = ["MES", "MNQ", "MYM", "M2K"]

# Dynamic equity discovery now lives in:
# - services/discovery_service.py
# - data/universe_filter.py
# - services/config_service.py
#
# This module intentionally keeps only the futures universe that is still
# used directly by UniverseFilter when building lane-specific watchlists.
