
def cluster_alerts(alerts):

    clustered = []
    seen = set()

    for alert in alerts:

        title = alert["title"].lower()

        key = " ".join(title.split()[:8])

        if key in seen:
            continue

        seen.add(key)

        clustered.append(alert)

    return clustered

