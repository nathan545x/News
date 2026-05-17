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

SOURCE_WEIGHTS = {
    "Bloomberg": 1.35,
    "Reuters": 1.35,
    "FT": 1.25,
    "WSJ": 1.25,
    "CNBC": 1.15,
    "CoinDesk": 1.10,
    "GoogleNews": 1.15,

    "SEC": 1.60,
    "Fed": 1.60,
    "Treasury": 1.50,
    "BOE": 1.60,
    "ECB": 1.60,
    "BOJ": 1.60,
    "IEA": 1.40,
    "OPEC": 1.50,
    "NATO": 1.40,
    "UN": 1.20,
}

FEEDS = [

    # =====================================================
    # BLOOMBERG DIRECT RSS
    # =====================================================

    ("Bloomberg", "Markets",
     "https://feeds.bloomberg.com/markets/news.rss"),

    ("Bloomberg", "Economics",
     "https://feeds.bloomberg.com/economics/news.rss"),

    ("Bloomberg", "Technology",
     "https://feeds.bloomberg.com/technology/news.rss"),

    ("Bloomberg", "Politics",
     "https://feeds.bloomberg.com/politics/news.rss"),

    ("Bloomberg", "Crypto",
     "https://feeds.bloomberg.com/crypto/news.rss"),

    # =====================================================
    # REUTERS DIRECT RSS
    # =====================================================

    ("Reuters", "World",
     "https://feeds.reuters.com/Reuters/worldNews"),

    ("Reuters", "Business",
     "https://feeds.reuters.com/reuters/businessNews"),

    ("Reuters", "Technology",
     "https://feeds.reuters.com/reuters/technologyNews"),

    # =====================================================
    # FINANCIAL TIMES DIRECT RSS
    # =====================================================

    ("FT", "Markets",
     "https://www.ft.com/markets?format=rss"),

    ("FT", "World",
     "https://www.ft.com/world?format=rss"),

    ("FT", "Companies",
     "https://www.ft.com/companies?format=rss"),

    # =====================================================
    # WSJ DIRECT RSS
    # =====================================================

    ("WSJ", "World",
     "https://feeds.a.dj.com/rss/RSSWorldNews.xml"),

    ("WSJ", "Markets",
     "https://feeds.a.dj.com/rss/RSSMarketsMain.xml"),

    ("WSJ", "Technology",
     "https://feeds.a.dj.com/rss/RSSTech.xml"),

    # =====================================================
    # CNBC DIRECT RSS
    # =====================================================

    ("CNBC", "Top News",
     "https://www.cnbc.com/id/100003114/device/rss/rss.html"),

    ("CNBC", "World",
     "https://www.cnbc.com/id/100727362/device/rss/rss.html"),

    ("CNBC", "Finance",
     "https://www.cnbc.com/id/10000664/device/rss/rss.html"),

    ("CNBC", "Technology",
     "https://www.cnbc.com/id/19854910/device/rss/rss.html"),

    # =====================================================
    # COINDESK DIRECT RSS
    # =====================================================

    ("CoinDesk", "Crypto",
     "https://www.coindesk.com/arc/outboundfeeds/rss/"),

    # =====================================================
    # BLOOMBERG VIA GOOGLE NEWS
    # =====================================================

    ("GoogleNews", "Bloomberg Latest",
     "https://news.google.com/rss/search?q=when:24h+allinurl:bloomberg.com&hl=en-US&gl=US&ceid=US:en"),

    ("GoogleNews", "Bloomberg Macro",
     "https://news.google.com/rss/search?q=site:bloomberg.com+fed+OR+inflation+OR+yield+OR+rates+OR+treasury&hl=en-US&gl=US&ceid=US:en"),

    ("GoogleNews", "Bloomberg Geopolitics",
     "https://news.google.com/rss/search?q=site:bloomberg.com+china+OR+ukraine+OR+iran+OR+taiwan+OR+sanctions&hl=en-US&gl=US&ceid=US:en"),

    ("GoogleNews", "Bloomberg Markets",
     "https://news.google.com/rss/search?q=site:bloomberg.com+stocks+OR+bonds+OR+oil+OR+commodities&hl=en-US&gl=US&ceid=US:en"),

    # =====================================================
    # REUTERS VIA GOOGLE NEWS
    # =====================================================

    ("GoogleNews", "Reuters Latest",
     "https://news.google.com/rss/search?q=when:24h+allinurl:reuters.com&hl=en-US&gl=US&ceid=US:en"),

    ("GoogleNews", "Reuters Macro",
     "https://news.google.com/rss/search?q=site:reuters.com+fed+OR+inflation+OR+yield+OR+rates+OR+treasury&hl=en-US&gl=US&ceid=US:en"),

    ("GoogleNews", "Reuters Geopolitics",
     "https://news.google.com/rss/search?q=site:reuters.com+china+OR+ukraine+OR+iran+OR+taiwan+OR+sanctions&hl=en-US&gl=US&ceid=US:en"),

    ("GoogleNews", "Reuters Markets",
     "https://news.google.com/rss/search?q=site:reuters.com+stocks+OR+bonds+OR+oil+OR+commodities&hl=en-US&gl=US&ceid=US:en"),

    ("GoogleNews", "Reuters Tech",
     "https://news.google.com/rss/search?q=site:reuters.com+nvidia+OR+AI+OR+openai+OR+semiconductors&hl=en-US&gl=US&ceid=US:en"),

    # =====================================================
    # FT VIA GOOGLE NEWS
    # =====================================================

    ("GoogleNews", "FT Latest",
     "https://news.google.com/rss/search?q=when:24h+allinurl:ft.com&hl=en-US&gl=US&ceid=US:en"),

    ("GoogleNews", "FT Macro",
     "https://news.google.com/rss/search?q=site:ft.com+fed+OR+ecb+OR+inflation+OR+rates+OR+yield&hl=en-US&gl=US&ceid=US:en"),

    ("GoogleNews", "FT Geopolitics",
     "https://news.google.com/rss/search?q=site:ft.com+china+OR+ukraine+OR+iran+OR+taiwan+OR+europe&hl=en-US&gl=US&ceid=US:en"),

    ("GoogleNews", "FT Markets",
     "https://news.google.com/rss/search?q=site:ft.com+stocks+OR+bonds+OR+oil+OR+commodities&hl=en-US&gl=US&ceid=US:en"),

    # =====================================================
    # WSJ VIA GOOGLE NEWS
    # =====================================================

    ("GoogleNews", "WSJ Latest",
     "https://news.google.com/rss/search?q=when:24h+allinurl:wsj.com&hl=en-US&gl=US&ceid=US:en"),

    ("GoogleNews", "WSJ Macro",
     "https://news.google.com/rss/search?q=site:wsj.com+fed+OR+inflation+OR+yield+OR+rates+OR+economy&hl=en-US&gl=US&ceid=US:en"),

    ("GoogleNews", "WSJ Geopolitics",
     "https://news.google.com/rss/search?q=site:wsj.com+china+OR+ukraine+OR+iran+OR+taiwan+OR+sanctions&hl=en-US&gl=US&ceid=US:en"),

    ("GoogleNews", "WSJ Markets",
     "https://news.google.com/rss/search?q=site:wsj.com+stocks+OR+bonds+OR+oil+OR+commodities&hl=en-US&gl=US&ceid=US:en"),

    ("GoogleNews", "WSJ Tech",
     "https://news.google.com/rss/search?q=site:wsj.com+nvidia+OR+AI+OR+openai+OR+semiconductors&hl=en-US&gl=US&ceid=US:en"),

    # =====================================================
    # CNBC VIA GOOGLE NEWS
    # =====================================================

    ("GoogleNews", "CNBC Latest",
     "https://news.google.com/rss/search?q=when:24h+allinurl:cnbc.com&hl=en-US&gl=US&ceid=US:en"),

    ("GoogleNews", "CNBC Macro",
     "https://news.google.com/rss/search?q=site:cnbc.com+fed+OR+inflation+OR+yield+OR+rates+OR+economy&hl=en-US&gl=US&ceid=US:en"),

    ("GoogleNews", "CNBC Geopolitics",
     "https://news.google.com/rss/search?q=site:cnbc.com+china+OR+ukraine+OR+iran+OR+taiwan+OR+sanctions&hl=en-US&gl=US&ceid=US:en"),

    ("GoogleNews", "CNBC Markets",
     "https://news.google.com/rss/search?q=site:cnbc.com+stocks+OR+bonds+OR+oil+OR+commodities&hl=en-US&gl=US&ceid=US:en"),

    ("GoogleNews", "CNBC Tech",
     "https://news.google.com/rss/search?q=site:cnbc.com+nvidia+OR+AI+OR+openai+OR+semiconductors&hl=en-US&gl=US&ceid=US:en"),

    # =====================================================
    # COINDESK VIA GOOGLE NEWS
    # =====================================================

    ("GoogleNews", "CoinDesk Latest",
     "https://news.google.com/rss/search?q=when:24h+allinurl:coindesk.com&hl=en-US&gl=US&ceid=US:en"),

    ("GoogleNews", "CoinDesk Markets",
     "https://news.google.com/rss/search?q=site:coindesk.com+bitcoin+OR+ethereum+OR+ETF+OR+stablecoin&hl=en-US&gl=US&ceid=US:en"),

    ("GoogleNews", "CoinDesk Regulation",
     "https://news.google.com/rss/search?q=site:coindesk.com+SEC+OR+crypto+lawsuit+OR+regulation+OR+ETF&hl=en-US&gl=US&ceid=US:en"),

    # =====================================================
    # GLOBAL MACRO
    # =====================================================

    ("GoogleNews", "Global Macro",
     "https://news.google.com/rss/search?q=fed+OR+ecb+OR+boj+OR+boe+OR+pboc+OR+inflation+OR+yield+OR+treasury&hl=en-US&gl=US&ceid=US:en"),

    ("GoogleNews", "Europe Macro",
     "https://news.google.com/rss/search?q=ECB+OR+Europe+OR+Germany+OR+France+OR+BOE+OR+gilts&hl=en-GB&gl=GB&ceid=GB:en"),

    ("GoogleNews", "Asia Macro",
     "https://news.google.com/rss/search?q=China+OR+Japan+OR+BOJ+OR+India+OR+PBOC+OR+yuan+OR+yen&hl=en-US&gl=US&ceid=US:en"),

    # =====================================================
    # GEOPOLITICS
    # =====================================================

    ("GoogleNews", "China Taiwan",
     "https://news.google.com/rss/search?q=China+OR+Taiwan+OR+Xi+OR+South+China+Sea+OR+export+controls&hl=en-US&gl=US&ceid=US:en"),

    ("GoogleNews", "Middle East",
     "https://news.google.com/rss/search?q=Iran+OR+Israel+OR+Saudi+OR+Gaza+OR+OPEC+OR+Hormuz+OR+Red+Sea&hl=en-US&gl=US&ceid=US:en"),

    ("GoogleNews", "Russia Ukraine",
     "https://news.google.com/rss/search?q=Russia+OR+Ukraine+OR+Putin+OR+sanctions+OR+NATO&hl=en-US&gl=US&ceid=US:en"),

    # =====================================================
    # ENERGY / SHIPPING
    # =====================================================

    ("GoogleNews", "Energy",
     "https://news.google.com/rss/search?q=oil+OR+crude+OR+OPEC+OR+LNG+OR+gas+OR+uranium&hl=en-US&gl=US&ceid=US:en"),

    ("GoogleNews", "Shipping",
     "https://news.google.com/rss/search?q=shipping+OR+Suez+OR+Hormuz+OR+Red+Sea+OR+port+OR+supply+chain&hl=en-US&gl=US&ceid=US:en"),

    # =====================================================
    # AI / CYBER
    # =====================================================

    ("GoogleNews", "AI",
     "https://news.google.com/rss/search?q=nvidia+OR+openai+OR+TSMC+OR+ASML+OR+semiconductor+OR+AI&hl=en-US&gl=US&ceid=US:en"),

    ("GoogleNews", "Cyber",
     "https://news.google.com/rss/search?q=cyberattack+OR+ransomware+OR+hacked+OR+outage+OR+data+breach&hl=en-US&gl=US&ceid=US:en"),

    # =====================================================
    # BROAD EVENTS
    # =====================================================

    ("GoogleNews", "Disruptions",
     "https://news.google.com/rss/search?q=strike+OR+shutdown+OR+protest+OR+evacuation+OR+wildfire+OR+earthquake+OR+labor&hl=en-US&gl=US&ceid=US:en"),

    # =====================================================
    # OFFICIAL SOURCES
    # =====================================================

    ("SEC", "Filings",
     "https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&output=atom"),

    ("Fed", "Rates",
     "https://www.federalreserve.gov/feeds/h15_data.htm"),

    ("Treasury", "Auctions",
     "https://www.treasurydirect.gov/rss/TAResults.xml"),

    ("Treasury", "Offerings",
     "https://www.treasurydirect.gov/rss/TAOfferingAnnouncement.xml"),

    ("BOE", "News",
     "https://www.bankofengland.co.uk/rss/news"),

    ("ECB", "Press",
     "https://www.ecb.europa.eu/rss/press.html"),

    ("ECB", "Speeches",
     "https://www.ecb.europa.eu/rss/speeches.html"),

    ("BOJ", "Notices",
     "https://www.boj.or.jp/en/rss/whatsnew.xml"),

    ("IEA", "Energy",
     "https://www.iea.org/rss/news.xml"),

    ("OPEC", "News",
     "https://www.opec.org/opec_web/en/rss/rss.xml"),

    ("NATO", "News",
     "https://www.nato.int/cps/en/natohq/rss.xml"),

    ("UN", "World",
     "https://news.un.org/feed/subscribe/en/news/all/rss.xml"),
]
