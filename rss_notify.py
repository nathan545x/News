
import json
import hashlib

from pathlib import Path

from datetime import datetime, timedelta

import feedparser

from engine.feeds import RSS_FEEDS

from engine.scoring import score_text

from engine.regimes import (
    detect_regime,
    classify_severity
)

from engine.extraction import (
    extract_tickers,
    extract_regions,
    extract_assets,
)

from engine.source_weights import (
    SOURCE_WEIGHTS
)

from engine.clustering import (
    cluster_alerts
)

from engine.impact import (
    market_impact
)

from engine.ntfy import (
    send_alert
)

from engine.why import (
    why_it_matters
)


ALERTS_PATH = Path("alerts.json")

SEEN_PATH = Path("seen.json")

SEEN_EXPIRY_HOURS = 6


def now():

    return (
        datetime.utcnow().isoformat()
        + "Z"
    )


def load_seen():

    if not SEEN_PATH.exists():
        return {}

    try:

        return json.loads(
            SEEN_PATH.read_text()
        )

    except:

        return {}


def save_seen(data):

    SEEN_PATH.write_text(
        json.dumps(data, indent=2)
    )


def uid(title, link):

    return hashlib.md5(
        f"{title}{link}".encode()
    ).hexdigest()


def cleanup_seen(seen):

    cleaned = {}

    for k, v in seen.items():

        try:

            dt = datetime.fromisoformat(
                v.replace("Z", "")
            )

            if (
                datetime.utcnow() - dt
                < timedelta(days=2)
            ):
                cleaned[k] = v

        except:
            pass

    return cleaned


def recently_seen(seen, alert_uid):

    last_seen = seen.get(alert_uid)

    if not last_seen:
        return False

    try:

        last_seen_dt = datetime.fromisoformat(
            last_seen.replace("Z", "")
        )

        return (

            datetime.utcnow() - last_seen_dt

            < timedelta(
                hours=SEEN_EXPIRY_HOURS
            )
        )

    except:

        return False


def build_market_regime(alerts):

    regime_scores = {}

    for alert in alerts:

        regime = alert["regime"]

        regime_scores[regime] = (

            regime_scores.get(regime, 0)

            + alert["score"]
        )

    dominant = "GENERAL"

    if regime_scores:

        dominant = max(
            regime_scores,
            key=regime_scores.get
        )

    return {

        "regime": dominant,

        "dominant_driver": dominant,

        "secondary_driver": "GENERAL",

        "signal_density":

            "HIGH"

            if len(alerts) > 20

            else "LOW",

        "critical_alerts":

            len([

                x for x in alerts

                if x["severity"] == "CRITICAL"

            ]),

        "high_alerts":

            len([

                x for x in alerts

                if x["severity"] == "HIGH"

            ]),

        "last_updated": now(),
    }


def main():

    print("\n========== RSS ENGINE START ==========\n")

    seen = load_seen()

    seen = cleanup_seen(seen)

    alerts = []

    print(
        "TOTAL FEED SOURCES:",
        len(RSS_FEEDS)
    )

    for source, feeds in RSS_FEEDS.items():

        print("\nSOURCE:", source)

        for feed_url in feeds:

            print("FETCHING:", feed_url)

            try:

                parsed = feedparser.parse(
                    feed_url
                )

            except Exception as e:

                print(
                    "FEED ERROR:",
                    source,
                    str(e)
                )

                continue

            print(
                "ENTRIES:",
                len(parsed.entries)
            )

            for entry in parsed.entries[:25]:

                title = entry.get(
                    "title",
                    ""
                )

                summary = entry.get(
                    "summary",
                    ""
                )

                link = entry.get(
                    "link",
                    ""
                )

                if not title:
                    continue

                alert_uid = uid(
                    title,
                    link
                )

                # =====================================
                # TEMP DEBUG
                # DEDUPE DISABLED
                # =====================================

                # if recently_seen(
                #     seen,
                #     alert_uid
                # ):
                #     continue

                text = f"""
{title}

{summary}
"""

                score, regime_scores = (
                    score_text(text)
                )

                source_weight = (
                    SOURCE_WEIGHTS.get(
                        source,
                        SOURCE_WEIGHTS["DEFAULT"]
                    )
                )

                score += source_weight

                regime = detect_regime(
                    regime_scores
                )

                severity = classify_severity(
                    score
                )

                tickers = extract_tickers(
                    text
                )

                regions = extract_regions(
                    text
                )

                assets = extract_assets(
                    text
                )

                alert = {

                    "id": alert_uid,

                    "title": title,

                    "summary": summary,

                    "link": link,

                    "source": source,

                    "score": score,

                    "severity": severity,

                    "regime": regime,

                    "tickers": tickers,

                    "regions": regions,

                    "assets": assets,

                    "market_impact":
                        market_impact(regime),

                    "why_it_matters":
                        why_it_matters(regime),

                    "published": now(),
                }

                alerts.append(alert)

                seen[alert_uid] = now()

                print(
                    "ALERT:",
                    severity,
                    "|",
                    regime,
                    "|",
                    source,
                    "|",
                    title[:80]
                )

    print(
        "\nRAW ALERT COUNT:",
        len(alerts)
    )

    alerts = cluster_alerts(alerts)

    print(
        "CLUSTERED ALERT COUNT:",
        len(alerts)
    )

    alerts = sorted(

        alerts,

        key=lambda x: x["score"],

        reverse=True
    )

    top_signals = alerts[:12]

    payload = {

        "terminal":
            "Institutional Macro Terminal",

        "generated_at":
            now(),

        "market_regime":
            build_market_regime(alerts),

        "top_signals":
            top_signals,

        "alerts":
            alerts,
    }

    ALERTS_PATH.write_text(

        json.dumps(
            payload,
            indent=2
        )
    )

    save_seen(seen)

    print(
        "\nFINAL ALERT COUNT:",
        len(alerts)
    )

    for alert in alerts:

        print(
            "\nSENDING ALERT:",
            alert["severity"],
            "|",
            alert["source"],
            "|",
            alert["title"][:100]
        )

        send_alert(alert)

    print(
        "\n========== RSS ENGINE COMPLETE ==========\n"
    )


if __name__ == "__main__":

    main()
