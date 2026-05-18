
import os
import requests


NEWS_TOPIC = os.getenv(
    "NTFY_TOPIC_NEWS",
    ""
)

URGENT_TOPIC = os.getenv(
    "NTFY_TOPIC_URGENT",
    ""
)


def post(topic, message):

    if not topic:
        return

    try:

        response = requests.post(
            f"https://ntfy.sh/{topic}",
            data=message.encode("utf-8"),
            timeout=15
        )

        print(
            f"NTFY {topic}:",
            response.status_code
        )

    except Exception as e:

        print("NTFY ERROR:", str(e))


def send_alert(alert):

    title = alert.get(
        "title",
        "No title"
    )

    severity = alert.get(
        "severity",
        "LOW"
    )

    regime = alert.get(
        "regime",
        "GENERAL"
    )

    source = alert.get(
        "source",
        "Unknown"
    )

    score = alert.get(
        "score",
        0
    )

    why = alert.get(
        "why_it_matters",
        ""
    )

    message = f"""
{severity} | {regime}

{title}

Source: {source}
Score: {score}

Why it matters:
{why}
"""

    # =====================================================
    # NORMAL FLOW
    # =====================================================

    post(
        NEWS_TOPIC,
        message
    )

    # =====================================================
    # URGENT FLOW
    # =====================================================

    if severity in {

        "HIGH",
        "CRITICAL"

    }:

        urgent_message = f"""
🚨 URGENT MARKET ALERT 🚨

{severity} | {regime}

{title}

Source: {source}
Score: {score}

Why it matters:
{why}
"""

        post(
            URGENT_TOPIC,
            urgent_message
        )

