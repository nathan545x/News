
SIGNAL_WEIGHTS = {

    "RATES": {

        # FED
        "fed": 6,
        "fomc": 7,
        "powell": 7,
        "rate hike": 8,
        "rate cut": 8,
        "yields": 5,
        "treasury": 4,

        # ECB
        "ecb": 8,
        "lagarde": 8,
        "eurozone inflation": 7,
        "bund yields": 6,
        "european central bank": 8,

        # BOE / UK
        "boe": 8,
        "bank of england": 8,
        "gilt": 7,
        "gilts": 7,
        "uk inflation": 8,
        "uk cpi": 8,
        "sterling": 5,
        "gbp": 5,

        # BOJ / JPY
        "boj": 9,
        "bank of japan": 9,
        "yen": 7,
        "jpy": 7,
        "yield curve control": 10,
        "ycc": 10,
        "jgb": 7,
    },

    "INFLATION": {
        "inflation": 7,
        "cpi": 8,
        "pce": 7,
        "ppi": 6,
        "sticky inflation": 9,
    },

    "GEO-SHOCK": {
        "war": 10,
        "iran": 8,
        "china": 6,
        "taiwan": 9,
        "missile": 8,
        "sanctions": 7,
        "military": 6,
    },

    "SYSTEMIC": {
        "bank failure": 12,
        "default": 11,
        "liquidity crisis": 12,
        "banking stress": 10,
        "contagion": 9,
    },

    "COMMODITIES": {
        "oil": 7,
        "opec": 8,
        "gold": 5,
        "copper": 4,
        "shipping": 5,
    },

    "CRYPTO": {
        "bitcoin": 5,
        "ethereum": 4,
        "crypto": 4,
        "etf": 5,
    },
}


def score_text(text):

    text = text.lower()

    total = 0
    regime_scores = {}

    for regime, terms in SIGNAL_WEIGHTS.items():

        score = 0

        for term, weight in terms.items():

            if term in text:
                score += weight

        if score:
            regime_scores[regime] = score
            total += score

    return total, regime_scores

