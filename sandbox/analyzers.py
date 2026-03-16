def expectancy(win_rate_pct: float, avg_win: float, avg_loss: float) -> float:
    win_rate=win_rate_pct/100.0
    loss_rate=1-win_rate
    return round((win_rate*avg_win) - (loss_rate*abs(avg_loss)), 4)
