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

    ("GoogleNews", "Bloomberg Latest", "https://news.google.com/rss/search?q=when:24h+allinurl:bloomberg.com&hl=en-US&gl=US&ceid=US:en"),
    ("GoogleNews", "Reuters Latest", "https://news.google.com/rss/search?q=when:24h+allinurl:reuters.com&hl=en-US&gl=US&ceid=US:en"),
    ("GoogleNews", "FT Latest", "https://news.google.com/rss/search?q=when:24h+allinurl:ft.com&hl=en-US&gl=US&ceid=US:en"),
    ("GoogleNews", "WSJ Latest", "https://news.google.com/rss/search?q=when:24h+allinurl:wsj.com&hl=en-US&gl=US&ceid=US:en"),
    ("GoogleNews", "CNBC Latest", "https://news.google.com/rss/search?q=when:24h+allinurl:cnbc.com&hl=en-US&gl=US&ceid=US:en"),
    ("GoogleNews", "CoinDesk Latest", "https://news.google.com/rss/search?q=when:24h+allinurl:coindesk.com&hl=en-US&gl=US&ceid=US:en"),

    ("GoogleNews", "Global Macro", "https://news.google.com/rss/search?q=fed+OR+ecb+OR+boj+OR+boe+OR+pboc+OR+inflation+OR+yield+OR+treasury&hl=en-US&gl=US&ceid=US:en"),
    ("GoogleNews", "Europe Macro", "https://news.google.com/rss/search?q=ECB+OR+Europe+OR+Germany+OR+France+OR+BOE+OR+gilts&hl=en-GB&gl=GB&ceid=GB:en"),
    ("GoogleNews", "Asia Macro", "https://news.google.com/rss/search?q=China+OR+Japan+OR+BOJ+OR+India+OR+PBOC+OR+yuan+OR+yen&hl=en-US&gl=US&ceid=US:en"),

    ("GoogleNews", "China Taiwan", "https://news.google.com/rss/search?q=China+OR+Taiwan+OR+Xi+OR+South+China+Sea+OR+export+controls&hl=en-US&gl=US&ceid=US:en"),
    ("GoogleNews", "Middle East", "https://news.google.com/rss/search?q=Iran+OR+Israel+OR+Saudi+OR+Gaza+OR+OPEC+OR+Hormuz+OR+Red+Sea&hl=en-US&gl=US&ceid=US:en"),
    ("GoogleNews", "Russia Ukraine", "https://news.google.com/rss/search?q=Russia+OR+Ukraine+OR+Putin+OR+sanctions+OR+NATO&hl=en-US&gl=US&ceid=US:en"),

    ("GoogleNews", "Energy", "https://news.google.com/rss/search?q=oil+OR+crude+OR+OPEC+OR+LNG+OR+gas+OR+uranium&hl=en-US&gl=US&ceid=US:en"),
    ("GoogleNews", "Shipping", "https://news.google.com/rss/search?q=shipping+OR+Suez+OR+Hormuz+OR+Red+Sea+OR+port+OR+supply+chain&hl=en-US&gl=US&ceid=US:en"),
    ("GoogleNews", "AI", "https://news.google.com/rss/search?q=nvidia+OR+openai+OR+TSMC+OR+ASML+OR+semiconductor+OR+AI&hl=en-US&gl=US&ceid=US:en"),
    ("GoogleNews", "Cyber", "https://news.google.com/rss/search?q=cyberattack+OR+ransomware+OR+hacked+OR+outage+OR+data+breach&hl=en-US&gl=US&ceid=US:en"),
    ("GoogleNews", "Disruptions", "https://news.google.com/rss/search?q=strike+OR+shutdown+OR+protest+OR+evacuation+OR+wildfire+OR+earthquake+OR+labor&hl=en-US&gl=US&ceid=US:en"),

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
        "fed": 10, "fomc": 10, "powell": 9, "inflation": 9,
        "cpi": 10, "ppi": 8, "yield": 7, "treasury": 7,
        "rates": 7, "rate cut": 10, "rate hike": 10,
        "ecb": 10, "boe": 9, "boj": 9, "pboc": 9,
    },
    "geopolitics": {
        "china": 6, "taiwan": 9, "iran": 9, "israel": 8,
        "ukraine": 9, "russia": 8, "sanctions": 9, "war": 10,
        "attack": 9, "nato": 8, "missile": 9,
    },
    "markets": {
        "stocks": 6, "bonds": 6, "oil": 8, "gold": 6,
        "commodities": 7, "yield": 7, "earnings": 6,
    },
    "ai": {
        "nvidia": 8, "nvda": 8, "openai": 7, "ai": 6,
        "semiconductor": 7, "tsmc": 7, "asml": 7,
    },
    "crypto": {
        "bitcoin": 8, "btc": 8, "ethereum": 7,
        "crypto": 5, "stablecoin": 5, "etf": 5,
    },
    "transport": {
        "shipping": 5, "port": 5, "rail": 4,
        "suez": 6, "hormuz": 8, "red sea": 7,
    },
    "disruptions": {
        "strike": 4, "shutdown": 5, "protest": 4,
        "outage": 5, "cyberattack": 7,
        "earthquake": 5, "wildfire": 5,
    },
}

NEGATIVE = [
    "celebrity", "fashion", "wine", "luxury", "restaurant"
]

STOPWORDS = {
    "the", "a", "an", "to", "of", "in", "on",
    "for", "and", "after", "with", "amid", "as", "by",
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

    score *= SOURCE_WEIGHTS.get(source, 1.0)

    return round(score, 1), sorted(matched_topics), matched_keywords

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

    history_ids = {
        alert.get("id") for alert in history if alert.get("id")
    }

    clusters = defaultdict(list)

    print(f"Loaded {len(seen)} seen items")
    print(f"Loaded {len(history)} historical alerts")

    for source, category, url in FEEDS:
        try:
            feed = feedparser.parse(url)
            entries = feed.entries or []

            print(f"{source} {category}: {len(entries)} entries")

            scored_count = 0

            for entry in entries[:25]:
                uid = item_id(source, category, entry)

                if uid in seen:
                    continue

                new_seen.add(uid)

                title = entry.get("title", "")
                score, topics, keywords = score_entry(source, entry)

                if score < 2:
                    continue

                scored_count += 1

                clusters[cluster_key(title)].append({
                    "source": source,
                    "category": category,
                    "title": title,
                    "link": entry.get("link", ""),
                    "score": score,
                    "topics": topics,
                    "keywords": keywords,
                    "time": now_iso(),
                })

            print(f"{source} {category}: {scored_count} new scored items")

        except Exception as e:
            print(f"Feed error: {source} {category}: {e}")

    new_alerts = []

    for cluster, stories in clusters.items():
        stories = sorted(
            stories,
            key=lambda x: x["score"],
            reverse=True,
        )

        best = stories[0]
        total_score = best["score"] + (len(stories) - 1) * 3
        source_count = len({s["source"] for s in stories})
        urgent = total_score >= 14
        sources = sorted({s["source"] for s in stories})

        alert = {
            "time": now_iso(),
            "urgent": urgent,
            "score": total_score,
            "sources": sources,
            "source_count": source_count,
            "topics": best["topics"],
            "keywords": best["keywords"][:5],
            "title": best["title"],
            "link": best["link"],
        }

        alert["id"] = alert_id(alert)

        if alert["id"] not in history_ids:
            new_alerts.append(alert)
            history_ids.add(alert["id"])

    new_alerts = sorted(
        new_alerts,
        key=lambda x: x["score"],
        reverse=True,
    )

    if not STATE_FILE.exists():
        save_seen(new_seen)
        save_alert_history(history)
        print("Initial setup complete.")
        return

    urgent_count = 0
    normal_count = 0

    for alert in new_alerts[:25]:
        title = (
            f"[{', '.join(alert['sources'])}] "
            f"{' | '.join(alert['topics'][:2])}"
        )

        if alert["source_count"] > 1:
            title += f" | {alert['source_count']} sources"

        body = (
            f"{alert['title']}\n\n"
            f"Score: {alert['score']}\n"
            f"Topics: {', '.join(alert['topics'])}\n"
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
            "score": 10,
            "sources": ["SYSTEM"],
            "source_count": 1,
            "topics": ["system"],
            "keywords": ["online"],
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
