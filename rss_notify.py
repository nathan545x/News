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
FORCE_REPOPULATE = False

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
    "nvidia": "NVDA", "nvda": "NVDA",
    "apple": "AAPL", "aapl": "AAPL",
    "microsoft": "MSFT", "msft": "MSFT",
    "amazon": "AMZN", "amzn": "AMZN",
    "meta": "META",
    "tesla": "TSLA", "tsla": "TSLA",
    "google": "GOOGL", "alphabet": "GOOGL", "googl": "GOOGL",
    "amd": "AMD",
    "intel": "INTC",
    "broadcom": "AVGO",
    "tsmc": "TSM",
    "asml": "ASML",
    "palantir": "PLTR", "pltr": "PLTR",
    "coinbase": "COIN",
    "bitcoin": "BTC", "btc": "BTC",
    "ethereum": "ETH", "eth": "ETH",
    "solana": "SOL",
    "xrp": "XRP",
}

REGIONS = {
    "US": ["fed", "treasury", "sec", "wall street", "nasdaq", "s&p", "dow", "united states"],
    "Europe": ["ecb", "europe", "eurozone", "germany", "france", "uk"],
    "China": ["china", "beijing", "pboc", "yuan"],
    "Taiwan": ["taiwan", "taipei", "south china sea"],
    "Japan": ["japan", "tokyo", "boj", "yen"],
    "India": ["india", "rbi", "rupee"],
    "Middle East": ["iran", "israel", "saudi", "gaza", "hormuz", "red sea"],
    "Russia/Ukraine": ["russia", "ukraine", "putin"],
}

ASSETS = {
    "Equities": ["stocks", "shares", "equities", "earnings", "ipo"],
    "Rates": ["rates", "yield", "treasury", "bonds", "gilts", "fomc", "fed", "ecb", "boj"],
    "FX": ["dollar", "yen", "yuan", "euro", "currency", "fx"],
    "Commodities": ["oil", "gold", "copper", "gas", "lng", "uranium", "opec"],
    "Crypto": ["bitcoin", "ethereum", "crypto", "stablecoin"],
    "Geopolitics": ["sanctions", "war", "attack", "missile", "taiwan", "iran", "ukraine"],
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
    ("Bloomberg", "Markets", "https://feeds.bloomberg.com/markets/news.rss"),
    ("Bloomberg", "Economics", "https://feeds.bloomberg.com/economics/news.rss"),
    ("Bloomberg", "Technology", "https://feeds.bloomberg.com/technology/news.rss"),
    ("Bloomberg", "Politics", "https://feeds.bloomberg.com/politics/news.rss"),
    ("Bloomberg", "Crypto", "https://feeds.bloomberg.com/crypto/news.rss"),

    ("Reuters", "World", "https://feeds.reuters.com/Reuters/worldNews"),
    ("Reuters", "Business", "https://feeds.reuters.com/reuters/businessNews"),
    ("Reuters", "Technology", "https://feeds.reuters.com/reuters/technologyNews"),

    ("FT", "Markets", "https://www.ft.com/markets?format=rss"),
    ("FT", "World", "https://www.ft.com/world?format=rss"),
    ("FT", "Companies", "https://www.ft.com/companies?format=rss"),

    ("WSJ", "World", "https://feeds.a.dj.com/rss/RSSWorldNews.xml"),
    ("WSJ", "Markets", "https://feeds.a.dj.com/rss/RSSMarketsMain.xml"),
    ("WSJ", "Technology", "https://feeds.a.dj.com/rss/RSSTech.xml"),

    ("CNBC", "Top News", "https://www.cnbc.com/id/100003114/device/rss/rss.html"),
    ("CNBC", "World", "https://www.cnbc.com/id/100727362/device/rss/rss.html"),
    ("CNBC", "Finance", "https://www.cnbc.com/id/10000664/device/rss/rss.html"),
    ("CNBC", "Technology", "https://www.cnbc.com/id/19854910/device/rss/rss.html"),

    ("CoinDesk", "Crypto", "https://www.coindesk.com/arc/outboundfeeds/rss/"),

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

    ("SEC", "Filings", "https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&output=atom"),
    ("Fed", "Rates", "https://www.federalreserve.gov/feeds/h15_data.htm"),
    ("Treasury", "Auctions", "https://www.treasurydirect.gov/rss/TAResults.xml"),
    ("Treasury", "Offerings", "https://www.treasurydirect.gov/rss/TAOfferingAnnouncement.xml"),
    ("BOE", "News", "https://www.bankofengland.co.uk/rss/news"),
    ("ECB", "Press", "https://www.ecb.europa.eu/rss/press.html"),
    ("ECB", "Speeches", "https://www.ecb.europa.eu/rss/speeches.html"),
    ("BOJ", "Notices", "https://www.boj.or.jp/en/rss/whatsnew.xml"),
    ("IEA", "Energy", "https://www.iea.org/rss/news.xml"),
    ("OPEC", "News", "https://www.opec.org/opec_web/en/rss/rss.xml"),
    ("NATO", "News", "https://www.nato.int/cps/en/natohq/rss.xml"),
    ("UN", "World", "https://news.un.org/feed/subscribe/en/news/all/rss.xml"),
]

TOPICS = {
    "macro": {
        "fed": 10, "fomc": 10, "inflation": 9, "cpi": 10,
        "yield": 7, "rates": 7, "ecb": 10, "boj": 9, "pboc": 9,
        "rate cut": 10, "rate hike": 10, "treasury": 8,
    },
    "geopolitics": {
        "china": 6, "taiwan": 9, "iran": 9, "israel": 8,
        "ukraine": 9, "russia": 8, "sanctions": 9, "war": 10,
        "attack": 9, "missile": 9, "nato": 8,
    },
    "markets": {
        "stocks": 6, "bonds": 6, "oil": 8, "gold": 6, "earnings": 6,
        "commodities": 7, "dollar": 6,
    },
    "ai": {
        "nvidia": 8, "openai": 7, "ai": 6,
        "semiconductor": 7, "semiconductors": 7, "tsmc": 7, "asml": 7,
    },
    "crypto": {
        "bitcoin": 8, "ethereum": 7, "crypto": 5, "stablecoin": 5, "etf": 5,
    },
    "transport": {
        "shipping": 5, "port": 5, "ports": 5, "suez": 6, "hormuz": 8, "red sea": 7,
    },
    "disruptions": {
        "strike": 4, "shutdown": 5, "protest": 4, "outage": 5, "cyberattack": 7,
    },
}

NEGATIVE = ["celebrity", "fashion", "wine", "luxury", "restaurant"]

STOPWORDS = {
    "the", "a", "an", "to", "of", "in", "on", "for",
    "and", "after", "with", "amid", "as", "by",
}

MACRO_CALENDAR_EVENTS = [
    {
        "name": "FOMC / Fed Decision",
        "keywords": ["fomc", "fed decision", "rate decision", "powell", "federal reserve"],
        "region": "US",
        "asset": "Rates",
        "severity": "HIGH",
    },
    {
        "name": "US CPI / Inflation",
        "keywords": ["cpi", "consumer price index", "inflation data", "inflation"],
        "region": "US",
        "asset": "Rates",
        "severity": "HIGH",
    },
    {
        "name": "US Jobs / NFP",
        "keywords": ["nonfarm payrolls", "payrolls", "jobs report", "unemployment"],
        "region": "US",
        "asset": "Rates",
        "severity": "HIGH",
    },
    {
        "name": "ECB Decision",
        "keywords": ["ecb decision", "lagarde", "eurozone rates", "ecb"],
        "region": "Europe",
        "asset": "Rates",
        "severity": "HIGH",
    },
    {
        "name": "BOJ Decision",
        "keywords": ["boj decision", "bank of japan", "yen rates", "boj"],
        "region": "Japan",
        "asset": "FX",
        "severity": "HIGH",
    },
    {
        "name": "Treasury Auction",
        "keywords": ["treasury auction", "auction results", "bid-to-cover", "tail"],
        "region": "US",
        "asset": "Rates",
        "severity": "MEDIUM",
    },
    {
        "name": "OPEC / Oil Event",
        "keywords": ["opec", "oil output", "crude production", "oil supply"],
        "region": "Global",
        "asset": "Commodities",
        "severity": "HIGH",
    },
]

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
    alerts = sorted(alerts, key=lambda x: x.get("time", ""), reverse=True)[:MAX_ALERTS]
    save_json(ALERTS_FILE, alerts)

def clean_text(value):
    return re.sub(r"\s+", " ", value.lower()).strip()

def entry_text(entry):
    return clean_text(f"{entry.get('title', '')} {entry.get('summary', '')}")

def keyword_matches(text, keyword):
    return re.search(rf"\b{re.escape(keyword.lower())}\b", text) is not None

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

def detect_macro_calendar(text):
    matches = []
    for event in MACRO_CALENDAR_EVENTS:
        for keyword in event["keywords"]:
            if keyword_matches(text, keyword):
                matches.append(event)
                break
    return matches

def get_severity(score, topics, regions, assets, keywords):
    text_bits = set([x.lower() for x in topics + regions + assets + keywords])

    critical_terms = {
        "war", "attack", "missile", "iran", "taiwan",
        "fomc", "cpi", "rate hike", "rate cut",
        "sanctions", "oil", "opec", "cyberattack"
    }

    high_terms = {
        "inflation", "fed", "ecb", "boj", "treasury",
        "yield", "china", "ukraine", "bitcoin", "nvidia"
    }

    if score >= 28 or text_bits & critical_terms:
        return "CRITICAL"

    if score >= 18 or text_bits & high_terms:
        return "HIGH"

    if score >= 10:
        return "MEDIUM"

    return "LOW"

def get_regime_tags(topics, regions, assets, keywords):
    text = " ".join(topics + regions + assets + keywords).lower()
    tags = []

    if any(x in text for x in ["war", "attack", "missile", "sanctions", "iran", "taiwan", "ukraine"]):
        tags.append("GEO-SHOCK")

    if any(x in text for x in ["cpi", "inflation", "ppi", "oil", "opec"]):
        tags.append("INFLATION")

    if any(x in text for x in ["fed", "ecb", "boj", "rate hike", "rate cut", "yield", "treasury", "rates"]):
        tags.append("RATES")

    if any(x in text for x in ["stocks", "equities", "earnings", "nvidia", "ai"]):
        tags.append("EQUITIES")

    if any(x in text for x in ["bitcoin", "ethereum", "crypto", "stablecoin"]):
        tags.append("CRYPTO")

    if any(x in text for x in ["oil", "gold", "copper", "gas", "lng", "uranium"]):
        tags.append("COMMODITIES")

    if any(x in text for x in ["cyberattack", "outage", "breach", "ransomware"]):
        tags.append("CYBER")

    if not tags:
        tags.append("GENERAL")

    return tags

def cluster_key(title):
    words = re.findall(r"\w+", title.lower())
    words = [w for w in words if w not in STOPWORDS and len(w) > 2]
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
    macro_calendar = detect_macro_calendar(text)

    if tickers:
        score += min(len(tickers) * 2, 6)
    if regions:
        score += min(len(regions), 4)
    if assets:
        score += min(len(assets), 4)
    if macro_calendar:
        score += 8

    score *= SOURCE_WEIGHTS.get(source, 1.0)

    return round(score, 1), sorted(matched_topics), matched_keywords, tickers, regions, assets, macro_calendar

def item_id(source, category, entry):
    unique = (
        entry.get("id")
        or entry.get("link")
        or hashlib.md5(entry.get("title", "").encode()).hexdigest()
    )
    return f"{source}:{category}:{unique}"

def alert_id(alert):
    raw = f"{alert.get('title', '')}:{alert.get('link', '')}"
    return hashlib.md5(raw.encode()).hexdigest()

def send_ntfy(title, body, topic, urgent=False):
    requests.post(
        f"https://ntfy.sh/{topic}",
        data=body.encode("utf-8"),
        headers={
            "Title": title,
            "Priority": "urgent" if urgent else "high",
            "Tags": "rotating_light" if urgent else "newspaper",
        },
        timeout=10,
    )

def main():
    seen = get_seen()
    new_seen = set(seen)
    history = get_alert_history()

    history_ids = {alert.get("id") for alert in history if alert.get("id")}
    clusters = defaultdict(list)

    print(f"Loaded {len(seen)} seen items")
    print(f"Loaded {len(history)} historical alerts")
    print(f"FORCE_REPOPULATE={FORCE_REPOPULATE}")

    for source, category, url in FEEDS:
        try:
            feed = feedparser.parse(url)
            entries = feed.entries or []

            print(f"{source} {category}: {len(entries)} entries")
            scored_count = 0

            for entry in entries[:25]:
                uid = item_id(source, category, entry)

                if uid in seen and not FORCE_REPOPULATE:
                    continue

                new_seen.add(uid)

                score, topics, keywords, tickers, regions, assets, macro_calendar = score_entry(source, entry)

                if score < 0:
                    continue

                scored_count += 1

                clusters[cluster_key(entry.get("title", ""))].append({
                    "source": source,
                    "category": category,
                    "title": entry.get("title", ""),
                    "link": entry.get("link", ""),
                    "score": score,
                    "topics": topics,
                    "keywords": keywords,
                    "tickers": tickers,
                    "regions": regions,
                    "assets": assets,
                    "macro_calendar_matches": macro_calendar,
                    "time": now_iso(),
                })

            print(f"{source} {category}: {scored_count} scored items")

        except Exception as e:
            print(f"Feed error: {source} {category}: {e}")

    new_alerts = []

    for cluster, stories in clusters.items():
        stories = sorted(stories, key=lambda x: x["score"], reverse=True)
        best = stories[0]

        total_score = best["score"] + (len(stories) - 1) * 3
        source_count = len({s["source"] for s in stories})
        sources = sorted({s["source"] for s in stories})

        all_tickers = sorted({t for s in stories for t in s.get("tickers", [])})[:10]
        all_regions = sorted({r for s in stories for r in s.get("regions", [])})[:10]
        all_assets = sorted({a for s in stories for a in s.get("assets", [])})[:10]
        all_macro_events = []
        for s in stories:
            for event in s.get("macro_calendar_matches", []):
                if event not in all_macro_events:
                    all_macro_events.append(event)

        severity = get_severity(total_score, best["topics"], all_regions, all_assets, best["keywords"])
        regime_tags = get_regime_tags(best["topics"], all_regions, all_assets, best["keywords"])

        alert = {
            "time": now_iso(),
            "urgent": severity in ["HIGH", "CRITICAL"],
            "severity": severity,
            "regime_tags": regime_tags,
            "score": total_score,
            "sources": sources,
            "source_count": source_count,
            "topics": best["topics"],
            "keywords": best["keywords"][:5],
            "tickers": all_tickers,
            "regions": all_regions,
            "assets": all_assets,
            "macro_calendar": bool(all_macro_events),
            "macro_events": all_macro_events,
            "title": best["title"],
            "link": best["link"],
        }

        alert["id"] = alert_id(alert)

        if alert["id"] not in history_ids or FORCE_REPOPULATE:
            new_alerts.append(alert)
            history_ids.add(alert["id"])

    new_alerts = sorted(new_alerts, key=lambda x: x["score"], reverse=True)

    urgent_count = 0
    normal_count = 0

    for alert in new_alerts[:25]:
        title = f"[{alert['severity']}] {'/'.join(alert.get('regime_tags', [])[:2])}"

        body = (
            f"{alert['title']}\n\n"
            f"Severity: {alert['severity']}\n"
            f"Regime: {', '.join(alert['regime_tags'])}\n"
            f"Score: {alert['score']}\n"
            f"Topics: {', '.join(alert['topics'])}\n"
            f"Tickers: {', '.join(alert['tickers'])}\n"
            f"Regions: {', '.join(alert['regions'])}\n"
            f"Assets: {', '.join(alert['assets'])}\n"
            f"Keywords: {', '.join(alert['keywords'])}\n\n"
            f"{alert['link']}"
        )

        send_ntfy(
            title,
            body,
            URGENT_TOPIC if alert["urgent"] else MARKET_TOPIC,
            urgent=alert["urgent"],
        )

        if alert["urgent"]:
            urgent_count += 1
        else:
            normal_count += 1

    combined_history = new_alerts + history

    if not combined_history:
        combined_history = [{
            "id": "system-online",
            "time": now_iso(),
            "urgent": False,
            "severity": "LOW",
            "regime_tags": ["GENERAL"],
            "score": 10,
            "sources": ["SYSTEM"],
            "source_count": 1,
            "topics": ["system"],
            "keywords": ["online"],
            "tickers": [],
            "regions": [],
            "assets": [],
            "macro_calendar": False,
            "macro_events": [],
            "title": "Market intelligence system online",
            "link": "https://github.com/nathan545x/News",
        }]

    save_seen(new_seen)
    save_alert_history(combined_history)

    print(f"New alerts this run: {len(new_alerts)}")
    print(f"Sent {normal_count} normal and {urgent_count} urgent alerts.")
    print(f"Saved {min(len(combined_history), MAX_ALERTS)} alerts to alerts.json")

if __name__ == "__main__":
    main()
