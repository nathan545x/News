#!/usr/bin/env python3
import os
import re
import json
import hashlib
import datetime as dt
from pathlib import Path
from urllib.parse import quote_plus

import feedparser
import requests


# =========================
# CONFIG
# =========================

BASE_DIR = Path(__file__).resolve().parent
ALERTS_PATH = BASE_DIR / "alerts.json"
SEEN_PATH = BASE_DIR / "seen.json"

MAX_ALERTS = int(os.getenv("MAX_ALERTS", "250"))
MAX_ITEMS_PER_FEED = int(os.getenv("MAX_ITEMS_PER_FEED", "25"))

NTFY_TOPIC = os.getenv("NTFY_TOPIC", "")
NTFY_URL = f"https://ntfy.sh/{NTFY_TOPIC}" if NTFY_TOPIC else ""

USER_AGENT = "MacroTerminalRSS/2.0"

ALLOWED_GOOGLE_DOMAINS = [
    "bloomberg.com",
    "reuters.com",
    "ft.com",
    "wsj.com",
    "cnbc.com",
    "coindesk.com",
]


# =========================
# FEEDS
# =========================

RSS_FEEDS = {
    "Bloomberg": [
        "https://feeds.bloomberg.com/markets/news.rss",
        "https://feeds.bloomberg.com/economics/news.rss",
        "https://feeds.bloomberg.com/politics/news.rss",
    ],
    "Reuters": [
        "https://www.reutersagency.com/feed/?best-topics=business-finance&post_type=best",
        "https://www.reutersagency.com/feed/?best-topics=political-general&post_type=best",
    ],
    "FT": [
        "https://www.ft.com/rss/home",
        "https://www.ft.com/markets?format=rss",
        "https://www.ft.com/global-economy?format=rss",
    ],
    "WSJ": [
        "https://feeds.a.dj.com/rss/RSSMarketsMain.xml",
        "https://feeds.a.dj.com/rss/WSJcomUSBusiness.xml",
    ],
    "CNBC": [
        "https://www.cnbc.com/id/100003114/device/rss/rss.html",
        "https://www.cnbc.com/id/10001147/device/rss/rss.html",
    ],
    "CoinDesk": [
        "https://www.coindesk.com/arc/outboundfeeds/rss/",
    ],
    "Official": [
        "https://www.sec.gov/news/pressreleases.rss",
        "https://www.ecb.europa.eu/rss/press.html",
        "https://www.federalreserve.gov/feeds/press_all.xml",
        "https://home.treasury.gov/news/press-releases/rss",
        "https://www.bankofjapan.or.jp/rss/en/release.xml",
        "https://www.opec.org/opec_web/en/rss_press.xml",
    ],
}


GOOGLE_QUERIES = [
    "Fed OR FOMC OR Powell OR Treasury yields",
    "CPI OR PCE OR inflation OR disinflation",
    "ECB OR BOJ OR BOE OR central bank",
    "oil OR Brent OR WTI OR OPEC",
    "China Taiwan OR Russia Ukraine OR Iran sanctions OR Red Sea",
    "bank failure OR liquidity crisis OR default OR contagion",
    "S&P 500 OR Nasdaq OR VIX OR dollar index",
    "Bitcoin ETF OR crypto regulation OR stablecoin",
]


def google_news_rss(query):
    domains = " OR ".join([f"site:{d}" for d in ALLOWED_GOOGLE_DOMAINS])
    q = quote_plus(f"({query}) ({domains})")
    return f"https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"


for q in GOOGLE_QUERIES:
    RSS_FEEDS.setdefault("GoogleNews", []).append(google_news_rss(q))


# =========================
# SIGNAL ENGINE
# =========================

SIGNAL_WEIGHTS = {
    "RATES": {
        "fed": 4, "fomc": 5, "powell": 5, "treasury yield": 5,
        "yields": 4, "rate cut": 6, "rate hike": 6, "dot plot": 6,
        "terminal rate": 5, "bond market": 3, "real yields": 5,
        "ecb": 4, "boj": 4, "boe": 4, "central bank": 4,
    },
    "INFLATION": {
        "cpi": 6, "core cpi": 7, "pce": 6, "core pce": 7,
        "ppi": 4, "inflation": 4, "wage growth": 4,
        "inflation expectations": 6, "disinflation": 5,
        "stagflation": 7,
    },
    "GEO-SHOCK": {
        "war": 6, "missile": 6, "sanctions": 5, "iran": 5,
        "israel": 4, "russia": 4, "ukraine": 4, "china": 4,
        "taiwan": 6, "red sea": 7, "houthi": 6, "nato": 4,
        "military": 5, "invasion": 8, "escalation": 7,
    },
    "COMMODITIES": {
        "oil": 4, "brent": 6, "wti": 6, "opec": 7,
        "natural gas": 5, "lng": 4, "gold": 4, "copper": 4,
        "supply disruption": 7, "inventory draw": 5,
    },
    "EQUITIES": {
        "s&p 500": 5, "nasdaq": 5, "dow": 3, "vix": 6,
        "earnings": 3, "stocks": 3, "equities": 4,
        "selloff": 5, "rally": 3, "futures": 3,
    },
    "CRYPTO": {
        "bitcoin": 5, "btc": 5, "ethereum": 4, "eth": 4,
        "crypto": 4, "stablecoin": 5, "etf": 3,
        "coinbase": 4, "binance": 4, "sec crypto": 6,
    },
    "CYBER": {
        "cyberattack": 7, "hack": 5, "ransomware": 6,
        "breach": 4, "outage": 4,
    },
    "SYSTEMIC": {
        "bank failure": 9, "default": 8, "contagion": 9,
        "liquidity crisis": 9, "emergency meeting": 9,
        "credit event": 8, "financial stability": 7,
        "bailout": 8, "bank run": 9,
    },
    "AI": {
        "artificial intelligence": 4, "ai": 3, "nvidia": 5,
        "semiconductor": 4, "chips": 4, "data center": 3,
    },
    "SHIPPING": {
        "shipping": 4, "freight": 4, "port": 3,
        "canal": 4, "red sea": 7, "suez": 6,
    },
}


SOURCE_WEIGHT = {
    "Official": 5,
    "Bloomberg": 4,
    "Reuters": 4,
    "FT": 4,
    "WSJ": 4,
    "CNBC": 2,
    "CoinDesk": 2,
    "GoogleNews": 1,
}


REGIME_PRIORITY = [
    "SYSTEMIC",
    "GEO-SHOCK",
    "RATES",
    "INFLATION",
    "COMMODITIES",
    "EQUITIES",
    "CRYPTO",
    "CYBER",
    "AI",
    "SHIPPING",
]


TICKER_MAP = {
    "apple": "AAPL", "microsoft": "MSFT", "nvidia": "NVDA",
    "tesla": "TSLA", "meta": "META", "amazon": "AMZN",
    "google": "GOOGL", "alphabet": "GOOGL",
    "coinbase": "COIN", "microstrategy": "MSTR",
    "bitcoin": "BTC", "ethereum": "ETH",
    "s&p 500": "SPX", "nasdaq": "NDX", "dow": "DJIA",
    "vix": "VIX", "dollar": "DXY", "gold": "XAU",
    "brent": "BRENT", "wti": "WTI",
}


REGION_KEYWORDS = {
    "US": ["us ", "u.s.", "america", "fed", "treasury", "white house", "washington"],
    "EU": ["europe", "eurozone", "ecb", "brussels", "germany", "france"],
    "UK": ["uk", "britain", "boe", "london"],
    "CHINA": ["china", "beijing", "pboc", "taiwan"],
    "JAPAN": ["japan", "boj", "tokyo", "yen"],
    "MIDDLE EAST": ["iran", "israel", "gaza", "red sea", "houthi", "saudi"],
    "RUSSIA/UKRAINE": ["russia", "ukraine", "moscow", "kyiv"],
    "GLOBAL": ["global", "world", "imf", "world bank", "opec"],
}


ASSET_KEYWORDS = {
    "Rates": ["yield", "treasury", "bond", "rates", "fomc", "central bank"],
    "FX": ["dollar", "yen", "euro", "sterling", "fx", "currency"],
    "Equities": ["stocks", "equities", "s&p", "nasdaq", "dow", "earnings"],
    "Commodities": ["oil", "brent", "wti", "gold", "copper", "gas"],
    "Crypto": ["bitcoin", "ethereum", "crypto", "stablecoin"],
    "Credit": ["credit", "default", "spreads", "debt", "liquidity"],
}


# =========================
# HELPERS
# =========================

def now_iso():
    return dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def clean_text(text):
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def normalize_url(url):
    return url.split("?")[0].strip() if url else ""


def make_id(title, link):
    raw = f"{title}|{normalize_url(link)}".lower()
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def load_json(path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text())
    except Exception:
        return default


def save_json(path, data):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False))


def fetch_feed(url):
    try:
        headers = {"User-Agent": USER_AGENT}
        res = requests.get(url, headers=headers, timeout=20)
        res.raise_for_status()
        return feedparser.parse(res.content)
    except Exception as e:
        print(f"[feed error] {url}: {e}")
        return None


def is_allowed_google_item(entry):
    text = f"{entry.get('title', '')} {entry.get('link', '')}".lower()
    return any(domain in text for domain in ALLOWED_GOOGLE_DOMAINS)


def published_time(entry):
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if parsed:
        return dt.datetime(*parsed[:6]).isoformat() + "Z"
    return now_iso()


# =========================
# EXTRACTION
# =========================

def score_item(title, summary, source):
    text = f"{title} {summary}".lower()
    regime_scores = {}
    matched_terms = []

    for regime, weights in SIGNAL_WEIGHTS.items():
        score = 0
        for term, weight in weights.items():
            if term.lower() in text:
                score += weight
                matched_terms.append(term)
        if score:
            regime_scores[regime] = score

    source_bonus = SOURCE_WEIGHT.get(source, 1)
    total_score = sum(regime_scores.values()) + source_bonus

    return total_score, regime_scores, sorted(set(matched_terms))


def detect_regime(regime_scores):
    if not regime_scores:
        return "GENERAL"

    sorted_regimes = sorted(
        regime_scores.items(),
        key=lambda x: (x[1], -REGIME_PRIORITY.index(x[0]) if x[0] in REGIME_PRIORITY else 0),
        reverse=True,
    )
    return sorted_regimes[0][0]


def classify_severity(score, source_count=1, is_official=False):
    if is_official and score >= 8:
        return "CRITICAL"
    if score >= 18 or source_count >= 4:
        return "CRITICAL"
    if score >= 11 or source_count >= 3:
        return "HIGH"
    if score >= 6:
        return "MEDIUM"
    return "LOW"


def extract_tickers(text):
    lower = text.lower()
    tickers = set()

    for key, ticker in TICKER_MAP.items():
        if key in lower:
            tickers.add(ticker)

    for match in re.findall(r"\$[A-Z]{1,5}\b", text):
        tickers.add(match.replace("$", ""))

    return sorted(tickers)


def extract_regions(text):
    lower = f" {text.lower()} "
    regions = []

    for region, keywords in REGION_KEYWORDS.items():
        if any(k in lower for k in keywords):
            regions.append(region)

    return sorted(set(regions)) or ["GLOBAL"]


def extract_assets(text):
    lower = text.lower()
    assets = []

    for asset, keywords in ASSET_KEYWORDS.items():
        if any(k in lower for k in keywords):
            assets.append(asset)

    return sorted(set(assets))


def market_impact(title, summary, regime):
    text = f"{title} {summary}".lower()
    impact = {}

    if any(x in text for x in ["hot inflation", "cpi rises", "inflation accelerates", "sticky inflation"]):
        impact.update({
            "rates": "bullish_yields",
            "equities": "risk_off",
            "usd": "bullish",
        })

    if any(x in text for x in ["rate cut", "cuts rates", "dovish", "lower rates"]):
        impact.update({
            "rates": "bullish_bonds",
            "equities": "risk_on",
            "usd": "bearish",
        })

    if any(x in text for x in ["rate hike", "hawkish", "higher for longer"]):
        impact.update({
            "rates": "bearish_bonds",
            "equities": "risk_off",
            "usd": "bullish",
        })

    if regime == "GEO-SHOCK":
        impact.update({
            "equities": "risk_off",
            "gold": "bullish",
        })

    if any(x in text for x in ["red sea", "iran", "opec", "oil supply", "brent", "wti"]):
        impact.update({
            "oil": "bullish",
            "inflation": "upside_risk",
        })

    if regime == "SYSTEMIC":
        impact.update({
            "equities": "risk_off",
            "credit": "wider_spreads",
            "rates": "bullish_bonds",
        })

    return impact


def explain_why_it_matters(regime, impact):
    if regime == "RATES":
        return "Rates-sensitive macro signal; likely relevant for yields, USD, duration, and equity multiples."
    if regime == "INFLATION":
        return "Inflation signal; may affect central-bank expectations, real yields, and risk assets."
    if regime == "GEO-SHOCK":
        return "Geopolitical shock risk; relevant for oil, gold, defense, shipping, and broad risk sentiment."
    if regime == "COMMODITIES":
        return "Commodity supply/demand signal; may feed into inflation expectations and sector rotation."
    if regime == "SYSTEMIC":
        return "Systemic risk signal; relevant for credit spreads, liquidity, banks, volatility, and safe-haven flows."
    if regime == "CRYPTO":
        return "Crypto market structure or regulation signal; relevant for BTC, ETH, exchanges, and risk appetite."
    if regime == "EQUITIES":
        return "Equity market signal; relevant for index direction, volatility, and sector leadership."
    return "Macro-relevant headline; monitor for cross-asset implications."


# =========================
# CLUSTERING
# =========================

def cluster_key(title):
    words = re.findall(r"[a-zA-Z0-9]+", title.lower())
    stop = {
        "the", "and", "for", "with", "from", "that", "this", "after",
        "over", "into", "amid", "says", "said", "will", "new", "are",
        "has", "have", "its", "not", "but", "you", "your"
    }
    important = [w for w in words if len(w) > 3 and w not in stop]
    return " ".join(sorted(important[:8]))


def cluster_alerts(items):
    clusters = {}

    for item in items:
        key = cluster_key(item["title"])
        if key not in clusters:
            clusters[key] = item
            clusters[key]["sources"] = [item["source"]]
            clusters[key]["source_count"] = 1
            clusters[key]["clustered_links"] = [item["link"]]
        else:
            existing = clusters[key]
            if item["source"] not in existing["sources"]:
                existing["sources"].append(item["source"])
            existing["source_count"] = len(existing["sources"])
            existing["clustered_links"].append(item["link"])
            existing["score"] = max(existing["score"], item["score"]) + 2
            existing["severity"] = classify_severity(
                existing["score"],
                existing["source_count"],
                existing.get("is_official", False),
            )

    return list(clusters.values())


# =========================
# NTFY
# =========================

def send_ntfy(alert):
    if not NTFY_URL:
        return

    if alert["severity"] not in {"HIGH", "CRITICAL"}:
        return

    title = f'{alert["severity"]} | {alert["regime"]}'
    body = (
        f'{alert["title"]}\n\n'
        f'{alert["why_it_matters"]}\n\n'
        f'Source: {alert["source"]}\n'
        f'Score: {alert["score"]}'
    )

    priority = "5" if alert["severity"] == "CRITICAL" else "4"

    try:
        requests.post(
            NTFY_URL,
            data=body.encode("utf-8"),
            headers={
                "Title": title,
                "Priority": priority,
                "Tags": "warning,chart_with_upwards_trend",
            },
            timeout=10,
        )
    except Exception as e:
        print(f"[ntfy error] {e}")


# =========================
# MAIN PIPELINE
# =========================

def collect_items():
    items = []

    for source, urls in RSS_FEEDS.items():
        for url in urls:
            feed = fetch_feed(url)
            if not feed:
                continue

            for entry in feed.entries[:MAX_ITEMS_PER_FEED]:
                if source == "GoogleNews" and not is_allowed_google_item(entry):
                    continue

                title = clean_text(entry.get("title", ""))
                summary = clean_text(entry.get("summary", ""))
                link = entry.get("link", "")

                if not title or not link:
                    continue

                text = f"{title} {summary}"
                score, regime_scores, matched_terms = score_item(title, summary, source)
                regime = detect_regime(regime_scores)
                is_official = source == "Official"

                severity = classify_severity(score, 1, is_official)
                impact = market_impact(title, summary, regime)

                item = {
                    "id": make_id(title, link),
                    "title": title,
                    "summary": summary,
                    "link": link,
                    "source": source,
                    "published": published_time(entry),
                    "collected_at": now_iso(),
                    "score": score,
                    "severity": severity,
                    "regime": regime,
                    "regime_scores": regime_scores,
                    "matched_terms": matched_terms,
                    "tickers": extract_tickers(text),
                    "regions": extract_regions(text),
                    "assets": extract_assets(text),
                    "market_impact": impact,
                    "why_it_matters": explain_why_it_matters(regime, impact),
                    "is_official": is_official,
                    "sources": [source],
                    "source_count": 1,
                    "clustered_links": [link],
                }

                if score >= 4 or severity in {"MEDIUM", "HIGH", "CRITICAL"}:
                    items.append(item)

    return items


def build_market_regime(alerts):
    recent = alerts[:75]

    regime_counts = {}
    critical_count = 0
    high_count = 0

    for alert in recent:
        regime = alert.get("regime", "GENERAL")
        regime_counts[regime] = regime_counts.get(regime, 0) + alert.get("score", 0)

        if alert.get("severity") == "CRITICAL":
            critical_count += 1
        if alert.get("severity") == "HIGH":
            high_count += 1

    if not regime_counts:
        dominant = "GENERAL"
    else:
        dominant = max(regime_counts.items(), key=lambda x: x[1])[0]

    if dominant in {"GEO-SHOCK", "SYSTEMIC"} or critical_count >= 2:
        regime_state = "RISK-OFF"
    elif dominant in {"RATES", "INFLATION"} and high_count >= 3:
        regime_state = "MACRO-TIGHTENING"
    elif dominant in {"EQUITIES", "CRYPTO"}:
        regime_state = "RISK-ON"
    else:
        regime_state = "MIXED"

    secondary = "GENERAL"
    if len(regime_counts) > 1:
        secondary = sorted(regime_counts.items(), key=lambda x: x[1], reverse=True)[1][0]

    density = "LOW"
    if len(recent) >= 50:
        density = "HIGH"
    elif len(recent) >= 20:
        density = "MEDIUM"

    return {
        "regime": regime_state,
        "dominant_driver": dominant,
        "secondary_driver": secondary,
        "signal_density": density,
        "critical_alerts": critical_count,
        "high_alerts": high_count,
        "last_updated": now_iso(),
    }


def main():
    seen = load_json(SEEN_PATH, {})
    existing_payload = load_json(ALERTS_PATH, {})
    existing_alerts = existing_payload.get("alerts", []) if isinstance(existing_payload, dict) else []

    raw_items = collect_items()
    clustered = cluster_alerts(raw_items)

    new_alerts = []

    for alert in clustered:
        if alert["id"] in seen:
            continue

        seen[alert["id"]] = {
            "title": alert["title"],
            "seen_at": now_iso(),
        }

        new_alerts.append(alert)

    all_alerts = new_alerts + existing_alerts
    all_alerts = sorted(
        all_alerts,
        key=lambda x: (
            {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}.get(x.get("severity"), 0),
            x.get("score", 0),
            x.get("published", ""),
        ),
        reverse=True,
    )[:MAX_ALERTS]

    payload = {
        "terminal": "Macro Market Intelligence",
        "generated_at": now_iso(),
        "market_regime": build_market_regime(all_alerts),
        "alerts": all_alerts,
    }

    save_json(ALERTS_PATH, payload)
    save_json(SEEN_PATH, seen)

    for alert in new_alerts:
        send_ntfy(alert)

    print(f"Collected {len(raw_items)} raw items")
    print(f"Clustered {len(clustered)} alerts")
    print(f"New alerts: {len(new_alerts)}")
    print(f"Saved {len(all_alerts)} total alerts")


if __name__ == "__main__":
    main()
