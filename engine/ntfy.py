
import os
import requests

TOPIC = os.getenv("NTFY_TOPIC", "")

def send_alert(alert):

    if not TOPIC:
        return

    if alert["severity"] not in {"MEDIUM", "HIGH", "CRITICAL"}:
        return

    try:
        requests.post(
            f"https://ntfy.sh/{TOPIC}",
            data=f'{alert["severity"]}: {alert["title"]}'.encode("utf-8"),
            timeout=10
        )
    except:
        pass

