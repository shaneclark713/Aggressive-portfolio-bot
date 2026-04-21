from __future__ import annotations

from typing import Dict, Iterable

SECTOR_MAP = {
    "NVDA": "Semiconductors",
    "AMD": "Semiconductors",
    "MU": "Semiconductors",
    "AAPL": "Technology",
    "MSFT": "Technology",
    "META": "Technology",
    "AMZN": "Consumer",
    "TSLA": "Automotive",
    "PLTR": "Software",
    "SMCI": "Hardware",
    "SOFI": "Financials",
    "HOOD": "Financials",
    "COIN": "Financials",
    "BAC": "Financials",
    "JPM": "Financials",
    "XOM": "Energy",
    "CVX": "Energy",
    "LLY": "Healthcare",
    "UNH": "Healthcare",
}


class SectorAnalyzer:
    def summarize(self, symbols: Iterable[str]) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for symbol in symbols:
            sector = SECTOR_MAP.get(str(symbol).upper(), "Other")
            counts[sector] = counts.get(sector, 0) + 1
        return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))
