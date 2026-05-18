
import json
from pathlib import Path
from datetime import datetime

alerts = [
    {
        "id":"1",
        "title":"Fed officials signal higher-for-longer rate path",
        "link":"https://www.reuters.com",
        "source":"Reuters",
        "severity":"HIGH",
        "regime":"RATES",
        "score":14,
        "published":datetime.utcnow().isoformat()+"Z",
        "tickers":["DXY","SPX","TLT"]
    },
    {
        "id":"2",
        "title":"Oil jumps on Middle East escalation concerns",
        "link":"https://www.bloomberg.com",
        "source":"Bloomberg",
        "severity":"CRITICAL",
        "regime":"GEO-SHOCK",
        "score":18,
        "published":datetime.utcnow().isoformat()+"Z",
        "tickers":["WTI","BRENT","XAU"]
    }
]

payload = {
    "terminal":"Macro Market Intelligence",
    "generated_at":datetime.utcnow().isoformat()+"Z",
    "market_regime":{
        "regime":"RISK-OFF",
        "dominant_driver":"GEO-SHOCK",
        "secondary_driver":"RATES",
        "signal_density":"HIGH",
        "critical_alerts":1
    },
    "top_signals":alerts,
    "alerts":alerts
}

Path("alerts.json").write_text(json.dumps(payload, indent=2))
Path("seen.json").write_text(json.dumps({}, indent=2))

print("alerts.json generated")
