from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict

import pandas as pd


class BaseStrategy(ABC):
    name: str = "Base Strategy"

    @abstractmethod
    def analyze(self, df: pd.DataFrame, symbol: str) -> Dict[str, Any]:
        raise NotImplementedError
