from __future__ import annotations


def analyze_sentiment(headlines: list[dict]) -> dict:
    bullish_words = ["surge", "beat", "upgraded", "record", "growth", "jump", "rally"]
    bearish_words = ["missed", "downgraded", "plunge", "lawsuit", "inflation", "drop", "fear"]
    bull = 0
    bear = 0
    for article in headlines:
        headline = str(article.get("headline", "")).lower()
        if any(word in headline for word in bullish_words):
            bull += 1
        if any(word in headline for word in bearish_words):
            bear += 1
    scored = bull + bear
    score = (bull - bear) / scored if scored else 0.0
    sentiment = "Bullish" if score > 0.3 else "Bearish" if score < -0.3 else "Neutral"
    return {"sentiment": sentiment, "score": round(score, 4), "bullish_articles": bull, "bearish_articles": bear}
