import json
import pathlib
import hashlib
import requests
import feedparser

MARKET_TOPIC = "MARKET_NEWS"
URGENT_TOPIC = "MARKET_URGENT"

STATE_FILE = pathlib.Path("seen.json")

FEEDS = [
    # Bloomberg
    ("Bloomberg", "Markets", "https://feeds.bloomberg.com/markets/news.rss"),
    ("Bloomberg", "Economics", "https://feeds.bloomberg.com/economics/news.rss"),
    ("Bloomberg", "Technology", "https://feeds.bloomberg.com/technology/news.rss"),
    ("Bloomberg", "Politics", "https://feeds.bloomberg.com/politics/news.rss"),
    ("Bloomberg", "Crypto", "https://feeds.bloomberg.com/crypto/news.rss"),
    ("Bloomberg", "Business", "https://feeds.bloomberg.com/business/news.rss"),
    ("Bloomberg", "Green", "https://feeds.bloomberg.com/green/news.rss"),

    # Reuters
    ("Reuters", "World", "https://feeds.reuters.com/Reuters/worldNews"),
    ("Reuters", "Business", "https://feeds.reuters.com/reuters/businessNews"),
    ("Reuters", "Technology", "https://feeds.reuters.com/reuters/technologyNews"),

    # Financial Times
    ("FT", "Markets", "https://www.ft.com/markets?format=rss"),
    ("FT", "World", "https://www.ft.com/world?format=rss"),

    # SEC
    ("SEC", "Latest Filings", "https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&output=atom"),

    # Federal Reserve
    ("Fed", "H15 Data", "https://www.federalreserve.gov/feeds/h15_data.htm"),

    # Treasury
    ("Treasury", "Auction Results", "https://www.treasurydirect.gov/rss/TAResults.xml"),
    ("Treasury", "Offering Announcements", "https://www.treasurydirect.gov/rss/TAOfferingAnnouncement.xml"),

    # Crypto
    ("CoinDesk", "Crypto", "https://www.coindesk.com/arc/outboundfeeds/rss/"),
]

KEYWORDS = [
    # Macro / Fed
    "fed", "federal reserve", "powell",
    "fomc", "beige book", "speech",
    "cpi", "inflation", "ppi",
    "yield", "treasury", "bond",
    "rate cut", "rate hike",
    "payrolls", "jobs", "gdp",
    "recession",

    # Treasury auctions
    "auction", "tail", "bid-to-cover",

    # AI / Tech
    "nvidia", "nvda", "openai",
    "microsoft", "msft",
    "apple", "aapl",
    "meta", "tesla", "tsla",
    "semiconductor", "chips",
    "asml", "tsmc",

    # Geopolitics
    "taiwan", "china",
    "ukraine", "russia",
    "iran", "israel",
    "tariffs", "sanctions",
    "trade war",
    "south china sea",

    # Commodities / Energy
    "oil", "crude", "opec",
    "lng", "uranium",
    "gold", "copper",
    "shipping", "red sea",
    "hormuz", "suez",

    # Crypto
    "bitcoin", "btc",
    "ethereum", "crypto",
    "etf", "stablecoin",
    "coinbase", "binance",

    # SEC / filings
    "8-k", "form 4", "insider",
    "s-1", "13d", "13g",
    "offering", "bankruptcy",
    "delisting", "material agreement",

    # Deals
    "earnings", "guidance",
    "merger", "acquisition",
    "ipo",
]

URGENT_KEYWORDS = [
    # Fed / macro
    "fed", "powell",
    "fomc",
    "cpi", "inflation",
    "rate cut", "rate hike",

    # Treasury / bonds
    "auction", "tail",

    # Geopolitics
    "tariffs", "sanctions",
    "war", "attack",
    "missile",
    "taiwan",
    "iran", "israel",
    "ukraine",

    # Commodities
    "oil", "opec",

    # AI / mega-cap
    "nvidia", "nvda",

    # Crypto
    "bitcoin", "btc",
    "etf",

    # SEC
    "8-k",
    "bankruptcy",
    "s-1",
]

NEGATIVE_KEYWORDS = [
    "wine",
    "luxury",
    "travel",
    "fashion",
    "restaurant",
    "celebrity",
]


def get_seen():
    if STATE_FILE.exists():
        return set(json.loads(STATE_FILE.read_text()))
    return set()


def save_seen(seen):
    STATE_FILE.write_text(json.dumps(sorted(list(seen)), indent=2))


def entry_text(entry):
    return (
        f"{entry.get('title', '')} "
        f"{entry.get('summary', '')}"
    ).lower()


def matched_keywords(entry, keywords):
    text = entry_text(entry)
    return [
        k for k in keywords
        if k.lower() in text
    ]


def item_id(source, category, entry):
    unique = (
        entry.get("id")
        or entry.get("link")
    )

    if not unique:
        unique = hashlib.md5(
            entry.get("title", "").encode()
        ).hexdigest()

    return f"{source}:{category}:{unique}"


def send_ntfy(source, category, entry, urgent=False):
    title = entry.get("title", "News Alert")
    link = entry.get("link", "")

    matches = matched_keywords(
        entry,
        URGENT_KEYWORDS if urgent else KEYWORDS
    )

    label = " | ".join(matches[:3])

    topic = (
        URGENT_TOPIC
        if urgent
        else MARKET_TOPIC
    )

    requests.post(
        f"https://ntfy.sh/{topic}",
        data=f"{title}\n\n{link}".encode("utf-8"),
        headers={
            "Title": f"[{source} {category}] {label}",
            "Priority": (
                "urgent"
                if urgent
                else "high"
            ),
            "Tags": (
                "rotating_light"
                if urgent
                else "chart_with_upwards_trend"
            ),
            "Click": link,
        },
        timeout=10,
    )


def main():
    seen = get_seen()
    new_seen = set(seen)

    normal_items = []
    urgent_items = []

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

                if matched_keywords(
                    entry,
                    NEGATIVE_KEYWORDS,
                ):
                    continue

                if matched_keywords(
                    entry,
                    URGENT_KEYWORDS,
                ):
                    urgent_items.append(
                        (source, category, entry)
                    )

                elif matched_keywords(
                    entry,
                    KEYWORDS,
                ):
                    normal_items.append(
                        (source, category, entry)
                    )

        except Exception as e:
            print(
                f"Feed failed: "
                f"{source} {category} "
                f"{e}"
            )

    if not STATE_FILE.exists():
        save_seen(new_seen)
        print(
            "Initial setup complete. "
            "No alerts sent."
        )
        return

    for source, category, entry in normal_items:
        send_ntfy(
            source,
            category,
            entry,
            urgent=False,
        )

    for source, category, entry in urgent_items:
        send_ntfy(
            source,
            category,
            entry,
            urgent=True,
        )

    save_seen(new_seen)

    print(
        f"Sent "
        f"{len(normal_items)} normal "
        f"and "
        f"{len(urgent_items)} urgent alerts."
    )


if __name__ == "__main__":
    main()
