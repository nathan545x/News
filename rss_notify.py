import json
import pathlib
import hashlib
import requests
import feedparser
import re
from collections import defaultdict
from datetime import datetime, timezone

MARKET_TOPIC = "MARKET_NEWS"
URGENT_TOPIC = "MARKET_URGENT"

STATE_FILE = pathlib.Path("seen.json")
ALERTS_FILE = pathlib.Path("alerts.json")

MAX_ALERTS = 150

SOURCE_WEIGHTS = {
    "Bloomberg": 1.35,
    "Reuters": 1.35,
    "FT": 1.25,
    "WSJ": 1.25,
    "CNBC": 1.15,
    "CoinDesk": 1.10,
    "GoogleNews": 1.15,

    "SEC": 1.60,
    "Fed": 1.60,
    "Treasury": 1.50,
    "BOE": 1.60,
    "ECB": 1.60,
    "BOJ": 1.60,
    "IEA": 1.40,
    "OPEC": 1.50,
    "NATO": 1.40,
    "UN": 1.20,
}

TICKERS = {
    "nvidia": "NVDA",
    "nvda": "NVDA",
    "apple": "AAPL",
    "aapl": "AAPL",
    "microsoft": "MSFT",
    "msft": "MSFT",
    "amazon": "AMZN",
    "amzn": "AMZN",
    "meta": "META",
    "tesla": "TSLA",
    "tsla": "TSLA",
    "google": "GOOGL",
    "alphabet": "GOOGL",
    "googl": "GOOGL",
    "amd": "AMD",
    "intel": "INTC",
    "intc": "INTC",
    "broadcom": "AVGO",
    "avgo": "AVGO",
    "tsmc": "TSM",
    "asml": "ASML",
    "palantir": "PLTR",
    "pltr": "PLTR",
    "coinbase": "COIN",
    "coin": "COIN",
    "microstrategy": "MSTR",
    "mstr": "MSTR",
    "bitcoin": "BTC",
    "btc": "BTC",
    "ethereum": "ETH",
    "eth": "ETH",
    "solana": "SOL",
    "xrp": "XRP",
}

REGIONS = {
    "US": [
        "fed", "treasury", "sec", "wall street",
        "nasdaq", "s&p", "dow", "united states"
    ],

    "Europe": [
        "ecb", "europe", "eurozone",
        "germany", "france", "uk"
    ],

    "China": [
        "china", "beijing", "pboc", "yuan"
    ],

    "Taiwan": [
        "taiwan", "taipei", "south china sea"
    ],

    "Japan": [
        "japan", "tokyo", "boj", "yen"
    ],

    "India": [
        "india", "rbi", "rupee"
    ],

    "Middle East": [
        "iran", "israel", "saudi",
        "gaza", "hormuz", "red sea"
    ],

    "Russia/Ukraine": [
        "russia", "ukraine", "putin"
    ],
}

ASSETS = {
    "Equities": [
        "stocks", "shares", "equities",
        "earnings", "ipo"
    ],

    "Rates": [
        "rates", "yield", "treasury",
        "bonds", "gilts"
    ],

    "FX": [
        "dollar", "yen", "yuan",
        "euro", "currency", "fx"
    ],

    "Commodities": [
        "oil", "gold", "copper",
        "gas", "lng", "uranium"
    ],

    "Crypto": [
        "bitcoin", "ethereum",
        "crypto", "stablecoin"
    ],

    "Geopolitics": [
        "sanctions", "war",
        "attack", "missile"
    ],
}

GOOGLE_NEWS_SOURCES = (
    "(site:bloomberg.com OR "
    "site:reuters.com OR "
    "site:ft.com OR "
    "site:wsj.com OR "
    "site:cnbc.com OR "
    "site:coindesk.com)"
)

FEEDS = [

    # =====================================================
    # DIRECT RSS
    # =====================================================

    ("Bloomberg", "Markets",
     "https://feeds.bloomberg.com/markets/news.rss"),

    ("Bloomberg", "Economics",
     "https://feeds.bloomberg.com/economics/news.rss"),

    ("Bloomberg", "Technology",
     "https://feeds.bloomberg.com/technology/news.rss"),

    ("Bloomberg", "Politics",
     "https://feeds.bloomberg.com/politics/news.rss"),

    ("Bloomberg", "Crypto",
     "https://feeds.bloomberg.com/crypto/news.rss"),

    ("Reuters", "World",
     "https://feeds.reuters.com/Reuters/worldNews"),

    ("Reuters", "Business",
     "https://feeds.reuters.com/reuters/businessNews"),

    ("Reuters", "Technology",
     "https://feeds.reuters.com/reuters/technologyNews"),

    ("FT", "Markets",
     "https://www.ft.com/markets?format=rss"),

    ("FT", "World",
     "https://www.ft.com/world?format=rss"),

    ("FT", "Companies",
     "https://www.ft.com/companies?format=rss"),

    ("WSJ", "World",
     "https://feeds.a.dj.com/rss/RSSWorldNews.xml"),

    ("WSJ", "Markets",
     "https://feeds.a.dj.com/rss/RSSMarketsMain.xml"),

    ("WSJ", "Technology",
     "https://feeds.a.dj.com/rss/RSSTech.xml"),

    ("CNBC", "Top News",
     "https://www.cnbc.com/id/100003114/device/rss/rss.html"),

    ("CNBC", "World",
     "https://www.cnbc.com/id/100727362/device/rss/rss.html"),

    ("CNBC", "Finance",
     "https://www.cnbc.com/id/10000664/device/rss/rss.html"),

    ("CNBC", "Technology",
     "https://www.cnbc.com/id/19854910/device/rss/rss.html"),

    ("CoinDesk", "Crypto",
     "https://www.coindesk.com/arc/outboundfeeds/rss/"),

    # =====================================================
    # GOOGLE NEWS FILTERED
    # =====================================================

    ("GoogleNews", "Latest",
     f"https://news.google.com/rss/search?q={GOOGLE_NEWS_SOURCES}+when:24h&hl=en-US&gl=US&ceid=US:en"),

    ("GoogleNews", "Macro",
     f"https://news.google.com/rss/search?q={GOOGLE_NEWS_SOURCES}+(fed OR inflation OR cpi OR rates OR yield OR treasury OR ecb OR boj OR pboc)&hl=en-US&gl=US&ceid=US:en"),

    ("GoogleNews", "Markets",
     f"https://news.google.com/rss/search?q={GOOGLE_NEWS_SOURCES}+(stocks OR bonds OR oil OR gold OR commodities OR earnings)&hl=en-US&gl=US&ceid=US:en"),

    ("GoogleNews", "Geopolitics",
     f"https://news.google.com/rss/search?q={GOOGLE_NEWS_SOURCES}+(china OR taiwan OR iran OR israel OR ukraine OR russia OR sanctions OR war)&hl=en-US&gl=US&ceid=US:en"),

    ("GoogleNews", "AI",
     f"https://news.google.com/rss/search?q={GOOGLE_NEWS_SOURCES}+(nvidia OR openai OR semiconductors OR ai OR tsmc OR asml)&hl=en-US&gl=US&ceid=US:en"),

    ("GoogleNews", "Energy",
     f"https://news.google.com/rss/search?q={GOOGLE_NEWS_SOURCES}+(oil OR opec OR lng OR uranium OR gas)&hl=en-US&gl=US&ceid=US:en"),

    ("GoogleNews", "Shipping",
     f"https://news.google.com/rss/search?q={GOOGLE_NEWS_SOURCES}+(shipping OR suez OR hormuz OR red sea OR supply chain OR ports)&hl=en-US&gl=US&ceid=US:en"),

    ("GoogleNews", "Crypto",
     f"https://news.google.com/rss/search?q={GOOGLE_NEWS_SOURCES}+(bitcoin OR ethereum OR crypto OR stablecoin OR etf OR coinbase)&hl=en-US&gl=US&ceid=US:en"),

    ("GoogleNews", "Cyber",
     f"https://news.google.com/rss/search?q={GOOGLE_NEWS_SOURCES}+(cyberattack OR ransomware OR hacked OR outage OR breach)&hl=en-US&gl=US&ceid=US:en"),

    ("GoogleNews", "Disruptions",
     f"https://news.google.com/rss/search?q={GOOGLE_NEWS_SOURCES}+(strike OR protest OR shutdown OR wildfire OR earthquake OR labor)&hl=en-US&gl=US&ceid=US:en"),

    # =====================================================
    # OFFICIAL SOURCES
    # =====================================================

    ("SEC", "Filings",
     "https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&output=atom"),

    ("Fed", "Rates",
     "https://www.federalreserve.gov/feeds/h15_data.htm"),

    ("Treasury", "Auctions",
     "https://www.treasurydirect.gov/rss/TAResults.xml"),

    ("Treasury", "Offerings",
     "https://www.treasurydirect.gov/rss/TAOfferingAnnouncement.xml"),

    ("BOE", "News",
     "https://www.bankofengland.co.uk/rss/news"),

    ("ECB", "Press",
     "https://www.ecb.europa.eu/rss/press.html"),

    ("ECB", "Speeches",
     "https://www.ecb.europa.eu/rss/speeches.html"),

    ("BOJ", "Notices",
     "https://www.boj.or.jp/en/rss/whatsnew.xml"),

    ("IEA", "Energy",
     "https://www.iea.org/rss/news.xml"),

    ("OPEC", "News",
     "https://www.opec.org/opec_web/en/rss/rss.xml"),

    ("NATO", "News",
     "https://www.nato.int/cps/en/natohq/rss.xml"),

    ("UN", "World",
     "https://news.un.org/feed/subscribe/en/news/all/rss.xml"),
]

TOPICS = {
    "macro": {
        "fed": 10,
        "fomc": 10,
        "inflation": 9,
        "cpi": 10,
        "yield": 7,
        "rates": 7,
        "ecb": 10,
        "boj": 9,
        "pboc": 9,
    },

    "geopolitics": {
        "china": 6,
        "taiwan": 9,
        "iran": 9,
        "israel": 8,
        "ukraine": 9,
        "russia": 8,
        "sanctions": 9,
        "war": 10,
    },

    "markets": {
        "stocks": 6,
        "bonds": 6,
        "oil": 8,
        "gold": 6,
        "earnings": 6,
    },

    "ai": {
        "nvidia": 8,
        "openai": 7,
        "ai": 6,
        "semiconductor": 7,
        "tsmc": 7,
        "asml": 7,
    },

    "crypto": {
        "bitcoin": 8,
        "ethereum": 7,
        "crypto": 5,
        "stablecoin": 5,
        "etf": 5,
    },

    "transport": {
        "shipping": 5,
        "port": 5,
        "suez": 6,
        "hormuz": 8,
        "red sea": 7,
    },

    "disruptions": {
        "strike": 4,
        "shutdown": 5,
        "protest": 4,
        "outage": 5,
        "cyberattack": 7,
    },
}

NEGATIVE = [
    "celebrity",
    "fashion",
    "wine",
    "luxury",
    "restaurant"
]

STOPWORDS = {
    "the", "a", "an", "to", "of", "in",
    "on", "for", "and", "after", "with",
    "amid", "as", "by",
}

def now_iso():
    return datetime.now(timezone.utc).isoformat()

def load_json(path, default):
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:
            return default
    return default

def save_json(path, data):
    path.write_text(json.dumps(data, indent=2))

def get_seen():
    return set(load_json(STATE_FILE, []))

def save_seen(seen):
    save_json(STATE_FILE, sorted(list(seen)))

def get_alert_history():
    data = load_json(ALERTS_FILE, [])
    return data if isinstance(data, list) else []

def save_alert_history(alerts):
    alerts = sorted(
        alerts,
        key=lambda x: x.get("time", ""),
        reverse=True,
    )[:MAX_ALERTS]

    save_json(ALERTS_FILE, alerts)

def clean_text(value):
    return re.sub(r"\s+", " ", value.lower()).strip()

def entry_text(entry):
    return clean_text(
        f"{entry.get('title', '')} {entry.get('summary', '')}"
    )

def keyword_matches(text, keyword):
    pattern = rf"\b{re.escape(keyword.lower())}\b"
    return re.search(pattern, text) is not None

def extract_from_map(text, mapping):
    results = set()

    for key, value in mapping.items():
        if isinstance(value, list):
            for term in value:
                if keyword_matches(text, term):
                    results.add(key)
        else:
            if keyword_matches(text, key):
                results.add(value)

    return sorted(results)

def extract_tickers(text):
    return extract_from_map(text, TICKERS)

def extract_regions(text):
    return extract_from_map(text, REGIONS)

def extract_assets(text):
    return extract_from_map(text, ASSETS)

def cluster_key(title):
    words = re.findall(r"\w+", title.lower())

    words = [
        w for w in words
        if w not in STOPWORDS and len(w) > 2
    ]

    return " ".join(sorted(words[:6]))

def score_entry(source, entry):
    text = entry_text(entry)

    score = 0
    matched_topics = set()
    matched_keywords = []

    for topic, keywords in TOPICS.items():
        for keyword, value in keywords.items():
            if keyword_matches(text, keyword):
                score += value
                matched_topics.add(topic)
                matched_keywords.append(keyword)

    for negative in NEGATIVE:
        if keyword_matches(text, negative):
            score -= 10

    tickers = extract_tickers(text)
    regions = extract_regions(text)
    assets = extract_assets(text)

    if tickers:
        score += min(len(tickers) * 2, 6)

    if regions:
        score += min(len(regions), 4)

    if assets:
        score += min(len(assets), 4)

    score *= SOURCE_WEIGHTS.get(source, 1.0)

    return (
        round(score, 1),
        sorted(matched_topics),
        matched_keywords,
        tickers,
        regions,
        assets,
    )
