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

    ("SEC", "Filings", "https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&output=atom"),
    ("Treasury", "Auctions", "https://www.treasurydirect.gov/rss/TAResults.xml"),
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
        "fed": 10, "fomc": 10, "powell": 9, "cpi": 10,
        "inflation": 9, "ppi": 8, "yield": 7, "treasury": 7,
        "rate cut": 10, "rate hike": 10, "jobs": 7, "recession": 8,
    },
    "geopolitics": {
        "taiwan": 9, "china": 5, "ukraine": 9, "russia": 8,
        "iran": 9, "israel": 8, "sanctions": 9, "tariffs": 8,
        "trade war": 8, "war": 10, "attack": 9, "missile": 9,
    },
    "ai": {
        "nvidia": 8, "nvda": 8, "openai": 7, "semiconductor": 7,
        "chips": 6, "asml": 7, "tsmc": 7, "microsoft": 6, "apple": 5,
    },
    "crypto": {
        "bitcoin": 8, "btc": 8, "ethereum": 6, "crypto": 5,
        "etf": 5, "coinbase": 5, "binance": 5,
    },
    "transport": {
        "strike": 3, "labor": 3, "union": 3, "shipping": 5,
        "port": 5, "rail": 4, "transport": 4, "supply chain": 6,
        "lirr": 5,
    },
    "energy": {
        "oil": 8, "crude": 8, "opec": 8, "lng": 6,
        "uranium": 6, "gold": 5, "copper": 5,
        "red sea": 7, "hormuz": 8, "suez": 6,
    },
    "sec": {
        "8-k": 8, "form 4": 6, "insider": 6, "s-1": 7,
        "13d": 7, "bankruptcy": 10, "offering": 5,
    },
    "general_news": {
        "strike": 3, "lawsuit": 4, "probe": 4, "investigation": 4,
        "outage": 5, "shutdown": 5, "hack": 6, "cyberattack": 7,
        "protest": 3, "evacuation": 5, "earthquake": 4, "wildfire": 4,
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
    if isinstance(data, list):
        return data
    return []

def save_alert_history(alerts):
    alerts = sorted(
        alerts,
        key=lambda x: x.get("time", ""),
        reverse=True,
    )[:MAX_ALERTS]

    save_json(ALERTS_FILE, alerts)

def clean_text(text):
    return re.sub(r"\s+", " ", text.lower()).strip()

def entry_text(entry):
    return clean_text(
        f"{entry.get('title', '')} {entry.get('summary', '')}"
    )

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
            if keyword in text:
                score += value
                matched_topics.add(topic)
                matched_keywords.append(keyword)

    for negative in NEGATIVE:
        if negative in text:
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
