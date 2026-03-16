def analyze_sentiment(headlines:list[dict]) -> dict:
    bullish=['surge','beat','upgraded','record','growth','jump','rally']
    bearish=['missed','downgraded','plunge','lawsuit','inflation','drop','fear']
    bull=bear=0
    for article in headlines:
        headline=str(article.get('headline','')).lower()
        if any(w in headline for w in bullish): bull+=1
        if any(w in headline for w in bearish): bear+=1
    scored=bull+bear; score=(bull-bear)/scored if scored else 0.0
    sentiment='Bullish' if score>0.3 else 'Bearish' if score<-0.3 else 'Neutral'
    return {'sentiment':sentiment,'score':round(score,4),'bullish_articles':bull,'bearish_articles':bear}
