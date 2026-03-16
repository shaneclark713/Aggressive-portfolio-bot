from abc import ABC, abstractmethod
import pandas as pd
class BaseStrategy(ABC):
    @abstractmethod
    def analyze(self, df: pd.DataFrame, symbol: str) -> dict: ...
