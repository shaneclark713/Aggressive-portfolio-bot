from dataclasses import dataclass
@dataclass(slots=True)
class SetupResult:
    symbol: str
    signal: str
    metadata: dict
