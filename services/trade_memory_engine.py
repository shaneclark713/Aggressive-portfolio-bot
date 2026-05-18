from __future__ import annotations

from collections import defaultdict
from typing import Any


class TradeMemoryEngine:
    """Adaptive trade memory and environment learning engine with Phase 9 persistence."""

    def __init__(self):
        self.playbook_stats = defaultdict(lambda:{"wins":0,"losses":0})
        self.personality_stats = defaultdict(lambda:{"wins":0,"losses":0})
        self.environment_stats = defaultdict(lambda:{"wins":0,"losses":0})
        self.autonomy_history=[]

    def snapshot(self, playbook, session_personality, trap_detection, probabilities):
        playbook_name=str(playbook.get('playbook') or 'Adaptive Tactical')
        personality=str(session_personality.get('personality') or 'balanced')
        trap_type=str(trap_detection.get('trap_type') or 'stable')
        environment_state=str(session_personality.get('environment_state') or 'balanced_rotation')

        trend_probability=int(probabilities.get('trend_probability') or 0)
        trap_probability=int(probabilities.get('trap_probability') or 0)
        environment_key=f"{environment_state}_trend_{trend_probability//10}_trap_{trap_probability//10}_{trap_type.lower().replace(' ','_')}"

        playbook_wr=self._win_rate(self.playbook_stats[playbook_name])
        personality_wr=self._win_rate(self.personality_stats[personality])
        environment_wr=self._win_rate(self.environment_stats[environment_key])

        confidence_adjustment=8 if environment_wr>=65 else -8 if environment_wr<=35 and environment_wr>0 else 0
        reinforcement_bias='aggressive' if environment_wr>=70 else 'defensive' if environment_wr<=35 and environment_wr>0 else 'balanced'

        recent=self.autonomy_history[-10:]
        autonomy_win_rate=self._history_win_rate(recent)

        return {
            'playbook_win_rate':playbook_wr,
            'personality_win_rate':personality_wr,
            'environment_win_rate':environment_wr,
            'confidence_adjustment':confidence_adjustment,
            'reinforcement_bias':reinforcement_bias,
            'environment_key':environment_key,
            'environment_state':environment_state,
            'autonomy_history_size':len(self.autonomy_history),
            'autonomy_win_rate':autonomy_win_rate,
        }

    def record_trade(self,playbook_name,personality,environment_key,outcome,review_score=None,adaptation_score=None,autonomy_score=None,environment_state=None):
        key='wins' if outcome.lower()=='win' else 'losses'
        self.playbook_stats[playbook_name][key]+=1
        self.personality_stats[personality][key]+=1
        self.environment_stats[environment_key][key]+=1
        self.autonomy_history.append({
            'outcome':outcome.lower(),
            'review_score':review_score,
            'adaptation_score':adaptation_score,
            'autonomy_score':autonomy_score,
            'environment_state':environment_state,
        })
        self.autonomy_history=self.autonomy_history[-250:]

    def _history_win_rate(self,rows):
        if not rows:
            return 0
        wins=sum(1 for r in rows if r.get('outcome')=='win')
        return int((wins/len(rows))*100)

    def _win_rate(self,stats):
        wins=int(stats.get('wins') or 0)
        losses=int(stats.get('losses') or 0)
        total=wins+losses
        return int((wins/total)*100) if total>0 else 0