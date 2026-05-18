from typing import Any


def build_confidence(probabilities: dict[str, Any]) -> dict[str, Any]:
    trend = float(probabilities.get('trend_probability', 50))
    mean_rev = float(probabilities.get('mean_reversion_probability', 50))

    score = round((trend + (100 - mean_rev)) / 2, 2)

    grade = 'A+'
    if score < 85:
        grade = 'A'
    if score < 75:
        grade = 'B'
    if score < 65:
        grade = 'C'

    return {
        'confidence_grade': grade,
        'confidence_score': score,
        'trend_probability': trend,
        'mean_reversion_probability': mean_rev,
    }
