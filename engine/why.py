
def why_it_matters(regime):

    MAP = {

        "RATES":
            "Central-bank repricing affecting yields, FX, liquidity and equities.",

        "INFLATION":
            "Inflation expectations impacting rate path, bonds and global risk assets.",

        "GEO-SHOCK":
            "Geopolitical escalation affecting commodities, shipping and cross-asset volatility.",

        "SYSTEMIC":
            "Potential liquidity or banking-system instability affecting financial conditions.",

        "COMMODITIES":
            "Commodity repricing impacting inflation expectations and industrial supply chains.",

        "CRYPTO":
            "Digital asset volatility and institutional crypto positioning changes.",

        "AI":
            "AI and semiconductor developments impacting tech leadership and capex cycles.",
    }

    return MAP.get(
        regime,
        "Macro-sensitive market development."
    )

