
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


def push(topic, title, message, priority="3"):

    if not topic:

        print("NO TOPIC")
        return

    try:

        response = requests.post(

            f"https://ntfy.sh/{topic}",

            data=message.encode("utf-8"),

            headers={

                "Title": title,

                "Priority": priority,

                "Tags": "warning,chart_with_upwards_trend"

            },

            timeout=15
        )

        print(
            f"NTFY PUSH [{topic}] =>",
            response.status_code
        )

    except Exception as e:

        print(
            "NTFY ERROR:",
            str(e)
        )


def send_alert(alert):

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

    title = alert.get(
        "title",
        "No title"
    )

    score = alert.get(
        "score",
        0
    )

    why = alert.get(
        "why_it_matters",
        ""
    )

    body = f"""
{severity} | {regime}

{title}

Source: {source}
Score: {score}

Why it matters:
{why}
"""

    # ==========================================
    # STANDARD FLOW
    # ==========================================

    if severity in {

        "MEDIUM",
        "HIGH",
        "CRITICAL"

    }:

        push(

            NEWS_TOPIC,

            f"{severity} | {regime}",

            body,

            priority="3"
        )

    # ==========================================
    # URGENT FLOW
    # ==========================================

    if severity in {

        "HIGH",
        "CRITICAL"

    }:

        urgent_body = f"""
🚨 URGENT MARKET ALERT 🚨

{severity} | {regime}

{title}

Source: {source}
Score: {score}

Why it matters:
{why}
"""

        push(

            URGENT_TOPIC,

            f"🚨 {severity} MARKET ALERT",

            urgent_body,

            priority="5"
        )

