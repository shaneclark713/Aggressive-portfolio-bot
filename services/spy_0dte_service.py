from __future__ import annotations

from datetime import date, datetime
from typing import Any
from zoneinfo import ZoneInfo
import pandas as pd

from data.sentiment import analyze_sentiment
from services.adaptive_exit_engine import AdaptiveExitEngine
from services.autonomous_scaling_engine import AutonomousScalingEngine
from services.cross_market_intelligence_service import CrossMarketIntelligenceService
from services.dealer_gamma_service import DealerGammaService
from services.execution_timing_engine import ExecutionTimingEngine
from services.market_narrative_engine import MarketNarrativeEngine
from services.probability_matrix_engine import ProbabilityMatrixEngine
from services.session_personality_engine import SessionPersonalityEngine
from services.tactical_playbook_engine import TacticalPlaybookEngine
from services.trade_memory_engine import TradeMemoryEngine
from services.trap_detection_engine import TrapDetectionEngine
from services.theta_decay_protection_engine import ThetaDecayProtectionEngine
from services.institutional_flow_expansion_engine import InstitutionalFlowExpansionEngine
from services.ai_trade_review_engine import AITradeReviewEngine
from services.autonomous_mutation_engine import AutonomousMutationEngine

class Spy0DteService:
    US_EVENT_COUNTRIES={"US","USA","UNITED STATES"}
    US_EVENT_KEYWORDS=("ppi","cpi","pce","fed","fomc")

    def __init__(self,telegram_app,chat_id:int,market_client,news_client,econ_client,tradier_client=None):
        self.telegram_app=telegram_app
        self.chat_id=chat_id
        self.market_client=market_client
        self.news_client=news_client
        self.econ_client=econ_client
        self.tradier_client=tradier_client
        self.market_tz=ZoneInfo('America/New_York')

        self.dealer_gamma=DealerGammaService()
        self.cross_market=CrossMarketIntelligenceService(market_client)
        self.narrative_engine=MarketNarrativeEngine()
        self.playbook_engine=TacticalPlaybookEngine()
        self.probability_engine=ProbabilityMatrixEngine()
        self.execution_timing_engine=ExecutionTimingEngine()
        self.adaptive_exit_engine=AdaptiveExitEngine()
        self.autonomous_scaling_engine=AutonomousScalingEngine()
        self.session_personality_engine=SessionPersonalityEngine()
        self.trap_detection_engine=TrapDetectionEngine()
        self.trade_memory_engine=TradeMemoryEngine()
        self.theta_decay_engine=ThetaDecayProtectionEngine()
        self.institutional_flow_engine=InstitutionalFlowExpansionEngine()
        self.ai_trade_review_engine=AITradeReviewEngine()
        self.autonomous_mutation_engine=AutonomousMutationEngine()

    async def analyze(self)->dict[str,Any]:
        minute_df=await self.market_client.get_historical_data('SPY',multiplier=5,timespan='minute')
        active=minute_df
        latest=float(active['close'].iloc[-1]) if not active.empty else 0.0
        rsi_5m=50.0
        vwap=latest
        dealer_gamma={}
        cross_market=await self.cross_market.analyze()
        structure={'score':0,'bias':'balanced'}
        narrative={}
        playbook={'playbook':'Adaptive Tactical'}
        probabilities=self.probability_engine.build(structure,dealer_gamma,cross_market,narrative,playbook,rsi_5m,latest,vwap)
        execution_timing=self.execution_timing_engine.analyze(structure,probabilities,latest,vwap)
        adaptive_exits=self.adaptive_exit_engine.evaluate(probabilities,playbook,structure,execution_timing,rsi_5m,latest,vwap)
        autonomous_scaling=self.autonomous_scaling_engine.plan(probabilities,playbook,adaptive_exits,execution_timing,rsi_5m)
        session_personality=self.session_personality_engine.classify(probabilities,structure,dealer_gamma,execution_timing,latest,vwap,rsi_5m)
        trap_detection=self.trap_detection_engine.detect(probabilities,structure,session_personality,execution_timing,latest,vwap,rsi_5m)
        trade_memory=self.trade_memory_engine.snapshot(playbook,session_personality,trap_detection,probabilities)

        theta_protection=self.theta_decay_engine.evaluate(probabilities,execution_timing,adaptive_exits,autonomous_scaling,session_personality,trap_detection,rsi_5m,latest,vwap)
        institutional_flow=self.institutional_flow_engine.evaluate(dealer_gamma,cross_market,probabilities,narrative,execution_timing,session_personality,trap_detection,latest,vwap,rsi_5m)
        ai_review=self.ai_trade_review_engine.review(playbook,probabilities,execution_timing,adaptive_exits,theta_protection,institutional_flow,trap_detection,trade_memory)
        autonomous_mutation=self.autonomous_mutation_engine.mutate(ai_review,probabilities,execution_timing,theta_protection,institutional_flow,trap_detection)

        return {'latest':latest,'vwap':vwap,'probabilities':probabilities,'trade_memory':trade_memory,'theta_protection':theta_protection,'institutional_flow':institutional_flow,'ai_review':ai_review,'autonomous_mutation':autonomous_mutation}
