
TICKERS = {

    # FX
    "usd": "DXY",
    "dollar": "DXY",
    "yen": "JPY",
    "jpy": "JPY",
    "sterling": "GBP",
    "gbp": "GBP",
    "euro": "EUR",

    # Commodities
    "gold": "XAU",
    "oil": "WTI",
    "brent": "BRENT",

    # Crypto
    "bitcoin": "BTC",
    "ethereum": "ETH",

    # Equities
    "nasdaq": "QQQ",
    "s&p": "SPY",
    "nvidia": "NVDA",

    # Rates
    "treasury": "TLT",
    "bund": "BUND",
    "gilt": "UK_GILTS",
    "jgb": "JGB",
}

REGIONS = {

    "united states": "US",
    "america": "US",

    "uk": "UK",
    "britain": "UK",
    "british": "UK",
    "england": "UK",
    "london": "UK",

    "europe": "EUROPE",
    "germany": "GERMANY",
    "france": "FRANCE",

    "japan": "JAPAN",
    "tokyo": "JAPAN",

    "china": "CHINA",
    "iran": "MIDDLE_EAST",
    "russia": "RUSSIA",
}

ASSETS = {

    "oil": "COMMODITIES",
    "gold": "COMMODITIES",

    "treasury": "RATES",
    "bund": "RATES",
    "gilt": "RATES",
    "jgb": "RATES",

    "bitcoin": "CRYPTO",

    "equities": "EQUITIES",
    "stocks": "EQUITIES",

    "yen": "FX",
    "sterling": "FX",
    "euro": "FX",
}


def extract_map(text, mapping):

    text = text.lower()

    found = []

    for k, v in mapping.items():

        if k in text:
            found.append(v)

    return sorted(set(found))


def extract_tickers(text):
    return extract_map(text, TICKERS)


def extract_regions(text):
    return extract_map(text, REGIONS)


def extract_assets(text):
    return extract_map(text, ASSETS)

