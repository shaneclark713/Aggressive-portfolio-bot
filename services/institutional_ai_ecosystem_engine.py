from __future__ import annotations
from typing import Any
from services.ai_consensus_engine import AIConsensusEngine

class InstitutionalAIEcosystemEngine:
    def __init__(self):
        self.consensus_engine=AIConsensusEngine()

    def build(self,payload:dict[str,Any])->dict[str,Any]:
        consensus=self.consensus_engine.evaluate(payload)
        memory=payload.get('trade_memory',{}) or {}
        review=payload.get('ai_review',{}) or {}
        ecosystem_score=int((consensus.get('consensus_score',50)+int(review.get('review_score',50))+int(memory.get('autonomy_win_rate',50)))/3)
        return {'ecosystem_score':ecosystem_score,'consensus':consensus,'ecosystem_label':'INSTITUTIONAL_ACTIVE' if ecosystem_score>=70 else 'BUILDING'}