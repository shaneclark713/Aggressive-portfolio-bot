import random

class MLScorer:
    def __init__(self, storage):
        self.storage = storage
        self.weights = self.storage.load("ml_weights") or {
            "rv": 1.0,
            "gap": 1.0,
            "float": 1.0,
            "news": 1.5
        }

    def score(self, trade):
        score = 0

        score += trade.get("relative_volume", 0) * self.weights["rv"]
        score += trade.get("gap_percent", 0) * self.weights["gap"]
        score += (1 / max(trade.get("float", 1), 1)) * self.weights["float"]

        if trade.get("news"):
            score += self.weights["news"]

        return score

    def update(self, trade, pnl):
        # simple reinforcement learning
        factor = 0.1 if pnl > 0 else -0.1

        self.weights["rv"] += factor * random.random()
        self.weights["gap"] += factor * random.random()

        self.storage.save("ml_weights", self.weights)
