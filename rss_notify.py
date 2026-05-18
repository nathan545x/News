
import json
import hashlib
from pathlib import Path
from datetime import datetime

import feedparser

from engine.feeds import RSS_FEEDS
from engine.scoring import score_text
from engine.regimes import detect_regime, classify_severity
from engine.extraction import (
    extract_tickers,
    extract_regions,
    extract_assets,
)
from engine.source_weights import SOURCE_WEIGHTS
from engine.clustering import cluster_alerts
from engine.impact import market_impact
from engine.ntfy import send_alert
from engine.why import why_it_matters


ALERTS_PATH = Path("alerts.json")
SEEN_PATH = Path("seen.json")


def now():
    return datetime.utcnow().isoformat() + "Z"


def load_seen():

    if not SEEN_PATH.exists():
        return {}

    return json.loads(SEEN_PATH.read_text())


def save_seen(data):
    SEEN_PATH.write_text(json.dumps(data, indent=2))


def uid(title, link):
    return hashlib.md5(f"{title}{link}".encode()).hexdigest()


def build_market_regime(alerts):

    scores = {}

    for alert in alerts:

        regime = alert["regime"]

        scores[regime] = scores.get(regime, 0) + alert["score"]

    dominant = "GENERAL"

    if scores:
        dominant = max(scores, key=scores.get)

    return {
        "regime": dominant,
        "dominant_driver": dominant,
        "secondary_driver": "GENERAL",
        "signal_density": "HIGH" if len(alerts) > 20 else "LOW",
        "critical_alerts": len([
            x for x in alerts
            if x["severity"] == "CRITICAL"
        ]),
        "high_alerts": len([
            x for x in alerts
            if x["severity"] == "HIGH"
        ]),
        "last_updated": now(),
    }


def main():

    seen = load_seen()

    alerts = []

    for source, feeds in RSS_FEEDS.items():

        for feed in feeds:

            parsed = feedparser.parse(feed)

            for entry in parsed.entries[:25]:

                title = entry.get("title", "")
                summary = entry.get("summary", "")
                link = entry.get("link", "")

                if not title:
                    continue

                alert_uid = uid(title, link)

                if alert_uid in seen:
                    continue

                text = f"{title} {summary}"

                score, regime_scores = score_text(text)

                source_weight = SOURCE_WEIGHTS.get(
                    source,
                    SOURCE_WEIGHTS["DEFAULT"]
                )

                score += source_weight

                regime = detect_regime(regime_scores)

                severity = classify_severity(score)

                alert = {

                    "id": alert_uid,

                    "title": title,
                    "summary": summary,
                    "link": link,

                    "source": source,

                    "score": score,
                    "severity": severity,
                    "regime": regime,

                    "tickers": extract_tickers(text),
                    "regions": extract_regions(text),
                    "assets": extract_assets(text),

                    "market_impact": market_impact(regime),

                    "why_it_matters": why_it_matters(regime),

                    "published": now(),
                }

                alerts.append(alert)

                seen[alert_uid] = now()

    alerts = cluster_alerts(alerts)

    alerts = sorted(
        alerts,
        key=lambda x: x["published"],
        reverse=True
    )

    top_signals = sorted(
        alerts,
        key=lambda x: x["score"],
        reverse=True
    )[:12]

    payload = {

        "terminal": "Institutional Macro Terminal",

        "generated_at": now(),

        "market_regime": build_market_regime(alerts),

        "top_signals": top_signals,

        "alerts": alerts,
    }

    ALERTS_PATH.write_text(
        json.dumps(payload, indent=2)
    )

    save_seen(seen)

    for alert in alerts:
        send_alert(alert)

    print(f"Generated {len(alerts)} alerts")


if __name__ == "__main__":
    main()

