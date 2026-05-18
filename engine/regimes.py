
def detect_regime(regime_scores):

    if not regime_scores:
        return "GENERAL"

    return sorted(
        regime_scores.items(),
        key=lambda x: x[1],
        reverse=True
    )[0][0]


def classify_severity(score):

    if score >= 25:
        return "CRITICAL"

    if score >= 15:
        return "HIGH"

    if score >= 8:
        return "MEDIUM"

    return "LOW"

