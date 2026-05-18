
SIGNAL_WEIGHTS = {

    # =========================================================
    # RATES / CENTRAL BANKS
    # =========================================================

    "RATES": {

        # FED
        "fed": 6,
        "fomc": 7,
        "powell": 7,
        "rate hike": 8,
        "rate cut": 8,
        "higher for longer": 9,
        "terminal rate": 8,
        "treasury": 4,
        "2-year yield": 7,
        "10-year yield": 6,
        "bond yields": 6,

        # ECB
        "ecb": 8,
        "lagarde": 8,
        "eurozone inflation": 7,
        "european central bank": 8,
        "bund yields": 6,

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
        "yen intervention": 10,
        "carry trade": 8,
    },

    # =========================================================
    # INFLATION
    # =========================================================

    "INFLATION": {

        "inflation": 7,
        "sticky inflation": 10,
        "disinflation": 8,

        "cpi": 8,
        "pce": 7,
        "ppi": 6,

        "price pressures": 6,
        "consumer prices": 6,
        "wage growth": 7,
        "services inflation": 8,
    },

    # =========================================================
    # GEOPOLITICS
    # =========================================================

    "GEO-SHOCK": {

        "war": 10,
        "middle east": 9,
        "iran": 8,
        "israel": 7,
        "missile": 8,
        "military": 6,
        "taiwan": 9,
        "china": 6,
        "russia": 7,
        "ukraine": 8,
        "sanctions": 7,
        "red sea": 8,
        "shipping disruption": 9,
        "conflict": 7,
        "nato": 7,
    },

    # =========================================================
    # SYSTEMIC / LIQUIDITY
    # =========================================================

    "SYSTEMIC": {

        "bank failure": 12,
        "default": 11,
        "liquidity crisis": 12,
        "banking stress": 10,
        "contagion": 9,
        "credit stress": 8,
        "commercial real estate": 8,
        "deleveraging": 7,
    },

    # =========================================================
    # COMMODITIES
    # =========================================================

    "COMMODITIES": {

        "oil": 8,
        "opec": 9,
        "gold": 6,
        "copper": 6,
        "silver": 5,
        "platinum": 7,

        "inventories": 5,
        "supply disruption": 9,
        "industrial metals": 7,
        "mining": 5,
        "refining": 5,
        "shipping": 5,
        "freight": 5,
    },

    # =========================================================
    # CRYPTO
    # =========================================================

    "CRYPTO": {

        "bitcoin": 6,
        "ethereum": 5,
        "crypto": 5,
        "etf": 5,
        "stablecoin": 6,
        "tokenization": 5,
    },

    # =========================================================
    # AI / SEMIS
    # =========================================================

    "AI": {

        "ai": 4,
        "artificial intelligence": 5,
        "nvidia": 7,
        "semiconductor": 6,
        "chip export": 7,
        "data center": 5,
    }
}


def score_text(text):

    text = text.lower()

    total = 0
    regime_scores = {}

    for regime, keywords in SIGNAL_WEIGHTS.items():

        regime_score = 0

        for keyword, weight in keywords.items():

            if keyword in text:
                regime_score += weight

        if regime_score:

            regime_scores[regime] = regime_score

            total += regime_score

    return total, regime_scores

