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

MAX_ALERTS = 20

FEEDS = [
    # Bloomberg
    ("Bloomberg", "Markets", "https://feeds.bloomberg.com/markets/news.rss"),
    ("Bloomberg", "Economics", "https://feeds.bloomberg.com/economics/news.rss"),
    ("Bloomberg", "Technology", "https://feeds.bloomberg.com/technology/news.rss"),
    ("Bloomberg", "Politics", "https://feeds.bloomberg.com/politics/news.rss"),
    ("Bloomberg", "Crypto", "https://feeds.bloomberg.com/crypto/news.rss"),

    # Reuters
    ("Reuters", "World", "https://feeds.reuters.com/Reuters/worldNews"),
    ("Reuters", "Business", "https://feeds.reuters.com/reuters/businessNews"),
    ("Reuters", "Technology", "https://feeds.reuters.com/reuters/technologyNews"),

    # FT
    ("FT", "Markets", "https://www.ft.com/markets?format=rss"),
    ("FT", "World", "https://www.ft.com/world?format=rss"),

    # SEC
    ("SEC", "Filings", "https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&output=atom"),

    # Treasury
    ("Treasury", "Auctions", "https://www.treasurydirect.gov/rss/TAResults.xml"),

    # Crypto
    ("CoinDesk", "Crypto", "https://www.coindesk.com/arc/outboundfeeds/rss/"),
]

SOURCE_WEIGHTS = {
    "Reuters": 1.4,
    "Bloomberg": 1.3,
    "FT": 1.2,
    "SEC": 1.6,
    "Treasury": 1.5,
    "CoinDesk": 1.1,
}

TOPICS = {
    "macro": {
        "fed": 10,
        "fomc": 10,
        "powell": 9,
        "cpi": 10,
        "inflation": 9,
        "ppi": 8,
        "yield": 7,
        "treasury": 7,
        "rate cut": 10,
        "rate hike": 10,
        "jobs": 7,
        "recession": 8,
    },

    "geopolitics": {
        "taiwan": 9,
        "china": 5,
        "ukraine": 9,
        "russia": 8,
        "iran": 9,
        "israel": 8,
        "sanctions": 9,
        "tariffs": 8,
        "trade war": 8,
        "war": 10,
        "attack": 9,
        "missile": 9,
    },

    "ai": {
        "nvidia": 8,
        "nvda": 8,
        "openai": 7,
        "semiconductor": 7,
        "chips": 6,
        "asml": 7,
        "tsmc": 7,
        "microsoft": 6,
        "apple": 5,
    },

    "crypto": {
        "bitcoin": 8,
        "btc": 8,
        "ethereum": 6,
        "crypto": 5,
        "etf": 5,
        "coinbase": 5,
        "binance": 5,
    },

    "transport": {
        "strike": 3,
        "labor": 3,
        "union": 3,
        "shipping": 5,
        "port": 5,
        "rail": 4,
        "transport": 4,
        "supply chain": 6,
        "lirr": 5,
    },

    "energy": {
        "oil": 8,
        "crude": 8,
        "opec": 8,
        "lng": 6,
        "uranium": 6,
        "gold": 5,
        "copper": 5,
        "red sea": 7,
        "hormuz": 8,
        "suez": 6,
    },

    "sec": {
        "8-k": 8,
        "form 4": 6,
        "insider": 6,
        "s-1": 7,
        "13d": 7,
        "bankruptcy": 10,
        "offering": 5,
    }
}

NEGATIVE = [
    "celebrity",
    "fashion",
    "wine",
    "luxury",
    "travel",
    "restaurant",
]

STOPWORDS = {
    "the", "a", "an", "to", "of", "in", "on",
    "for", "and", "after", "with", "amid",
}

def now_iso():
    return datetime.now(timezone.utc).isoformat()

def get_seen():
    if STATE_FILE.exists():
        return set(json.loads(STATE_FILE.read_text()))
    return set()

def save_seen(seen):
    STATE_FILE.write_text(
        json.dumps(sorted(list(seen)), indent=2)
    )

def save_alerts(alerts):
    ALERTS_FILE.write_text(
        json.dumps(alerts, indent=2)
    )

def clean_text(text):
    return re.sub(r"\s+", " ", text.lower()).strip()

def entry_text(entry):
    return clean_text(
        f"{entry.get('title', '')} "
        f"{entry.get('summary', '')}"
    )

def cluster_key(title):
    words = re.findall(r"\w+", title.lower())

    words = [
        w for w in words
        if w not in STOPWORDS and len(w) > 2
    ]

    words = sorted(words[:6])

    return " ".join(words)

def score_entry(source, entry):
    text = entry_text(entry)

    score = 0
    matched_topics = set()
    matched_keywords = []

    for topic, keywords in TOPICS.items():
        for keyword, value in keywords.items():
            if keyword in text:
                score += value
                matched_topics.add(topic)
                matched_keywords.append(keyword)

    for negative in NEGATIVE:
        if negative in text:
            score -= 10

    score *= SOURCE_WEIGHTS.get(source, 1.0)

    return (
        round(score, 1),
        list(matched_topics),
        matched_keywords,
    )

def item_id(source, category, entry):
    unique = (
        entry.get("id")
        or entry.get("link")
        or hashlib.md5(
            entry.get("title", "").encode()
        ).hexdigest()
    )

    return f"{source}:{category}:{unique}"

def send_ntfy(
    title,
    body,
    topic,
    urgent=False,
):
    requests.post(
        f"https://ntfy.sh/{topic}",
        data=body.encode("utf-8"),
        headers={
            "Title": title,
            "Priority": (
                "urgent"
                if urgent
                else "high"
            ),
            "Tags": (
                "rotating_light"
                if urgent
                else "newspaper"
            ),
        },
        timeout=10,
    )

def main():
    seen = get_seen()
    new_seen = set(seen)

    clusters = defaultdict(list)

    for source, category, url in FEEDS:
        try:
            feed = feedparser.parse(url)

            for entry in feed.entries[:20]:

                uid = item_id(
                    source,
                    category,
                    entry,
                )

                if uid in seen:
                    continue

                new_seen.add(uid)

                title = entry.get("title", "")

                score, topics, keywords = score_entry(
                    source,
                    entry,
                )

                if score < 5:
                    continue

                cluster = cluster_key(title)

                clusters[cluster].append({
                    "source": source,
                    "category": category,
                    "title": title,
                    "link": entry.get("link", ""),
                    "score": score,
                    "topics": topics,
                    "keywords": keywords,
                    "time": now_iso(),
                })

        except Exception as e:
            print(f"Feed error: {source} {e}")

    alerts = []

    for cluster, stories in clusters.items():

        stories = sorted(
            stories,
            key=lambda x: x["score"],
            reverse=True,
        )

        best = stories[0]

        total_score = (
            best["score"]
            + (len(stories) - 1) * 3
        )

        source_count = len({
            s["source"] for s in stories
        })

        urgent = total_score >= 18

        sources = sorted({
            s["source"] for s in stories
        })

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

        alerts.append(alert)

    alerts = sorted(
        alerts,
        key=lambda x: x["score"],
        reverse=True,
    )[:MAX_ALERTS]

    if not STATE_FILE.exists():
        save_seen(new_seen)
        save_alerts([])
        print("Initial setup complete.")
        return

    urgent_count = 0
    normal_count = 0

    for alert in alerts:

        title = (
            f"[{', '.join(alert['sources'])}] "
            f"{' | '.join(alert['topics'][:2])}"
        )

        if alert["source_count"] > 1:
            title += (
                f" | "
                f"{alert['source_count']} sources"
            )

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
            URGENT_TOPIC
            if alert["urgent"]
            else MARKET_TOPIC,
            urgent=alert["urgent"],
        )

        if alert["urgent"]:
            urgent_count += 1
        else:
            normal_count += 1

    save_seen(new_seen)
    save_alerts(alerts)

    print(
        f"Sent "
        f"{normal_count} normal "
        f"and "
        f"{urgent_count} urgent alerts."
    )

if __name__ == "__main__":
    main()
