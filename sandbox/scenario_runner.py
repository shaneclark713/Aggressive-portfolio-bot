class ScenarioRunner:
    def __init__(self, engine): self.engine=engine
    def run(self, strategy_class, df): return self.engine.run_historical_probability(strategy_class, df)
