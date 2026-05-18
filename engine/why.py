
def why_it_matters(regime):

    MAP = {

        "RATES":
            "Central-bank repricing affecting yields, FX, liquidity and equities.",

        "INFLATION":
            "Inflation expectations affecting rate path and global bond markets.",

        "GEO-SHOCK":
            "Geopolitical escalation affecting commodities and cross-asset volatility.",

        "SYSTEMIC":
            "Potential banking or liquidity instability impacting global markets.",

        "CRYPTO":
            "Institutional crypto positioning and digital asset volatility.",

        "COMMODITIES":
            "Commodity repricing impacting inflation expectations and supply chains.",
    }

    return MAP.get(
        regime,
        "Macro-sensitive market development."
    )

