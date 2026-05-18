from __future__ import annotations

from typing import Any


class MarketNarrativeEngine:
    """Institutional-style market narrative synthesis layer.

    Converts raw market conditions into tactical explanations the scan engine
    can use for higher-quality desk-style reports.
    """

    def build(
        self,
        structure: dict[str, Any],
        dealer_gamma: dict[str, Any],
        cross_market: dict[str, Any],
        sentiment: dict[str, Any],
        rsi_5m: float,
        latest: float,
        vwap: float,
    ) -> dict[str, Any]:
        narratives: list[str] = []
        tactical: list[str] = []
        risks: list[str] = []

        structure_bias = str(structure.get("bias", "balanced / tactical"))
        dealer_regime = str(dealer_gamma.get("dealer_regime", "balanced dealer pressure"))
        cross_tone = str(cross_market.get("tone", "mixed / neutral"))
        sentiment_label = str(sentiment.get("sentiment", "neutral"))

        if "upside" in structure_bias and "risk-on" in cross_tone:
            narratives.append("Momentum continuation environment supported by broader risk appetite.")
            tactical.append("Favor ORB continuation setups over mean-reversion fades.")

        if "downside" in structure_bias and "risk-off" in cross_tone:
            narratives.append("Defensive cross-market behavior supports downside continuation risk.")
            tactical.append("Favor failed-bounce setups unless VWAP is reclaimed cleanly.")

        if "pin risk" in dealer_regime:
            narratives.append("Dealer positioning still favors intraday pinning and rotational chop.")
            tactical.append("Reduce aggression inside opening range and avoid chasing extension.")

        if "call-heavy" in dealer_regime:
            narratives.append("Call-side pressure increases probability of squeeze continuation above resistance.")
            tactical.append("Allow runners only after confirmed ORB acceptance.")

        if "put-heavy" in dealer_regime:
            narratives.append("Put-side hedge pressure increases downside acceleration risk under support.")
            tactical.append("Watch for failed VWAP reclaims and liquidity flushes.")

        if latest > vwap:
            tactical.append("Price above VWAP keeps institutional control with buyers until proven otherwise.")
        elif latest < vwap:
            tactical.append("Price below VWAP keeps institutional control with sellers until proven otherwise.")

        if rsi_5m >= 72:
            risks.append("RSI stretched; failed breakout probability increasing.")
        elif rsi_5m <= 32:
            risks.append("RSI compressed; reflex bounce risk elevated.")
        else:
            tactical.append("RSI remains inside a tradable continuation/reversion band.")

        if sentiment_label == "negative":
            risks.append("Headline sentiment remains defensive; monitor volatility expansion carefully.")
        elif sentiment_label == "positive":
            tactical.append("Headline sentiment remains supportive of continuation flows.")

        if not narratives:
            narratives.append("Market remains rotational with mixed institutional confirmation.")

        if not tactical:
            tactical.append("Wait for confirmation instead of forcing directional exposure.")

        if not risks:
            risks.append("No abnormal institutional risk signal beyond standard 0DTE volatility.")

        environment = self._environment_label(structure_bias, dealer_regime, cross_tone)

        return {
            "environment": environment,
            "narratives": narratives[:5],
            "tactical": tactical[:6],
            "risks": risks[:5],
        }

    def _environment_label(self, structure_bias: str, dealer_regime: str, cross_tone: str) -> str:
        if "upside" in structure_bias and "risk-on" in cross_tone:
            return "AI / momentum continuation environment"

        if "downside" in structure_bias and "risk-off" in cross_tone:
            return "risk-off / defensive environment"

        if "pin risk" in dealer_regime:
            return "gamma-pin rotational environment"

        return "balanced tactical environment"
