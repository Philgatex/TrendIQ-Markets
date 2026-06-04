import os
from datetime import datetime, timedelta
from typing import Dict, List

import requests

NEWSAPI_URL = "https://newsapi.org/v2/everything"


def fetch_market_news(query: str = "market OR stocks OR crypto OR forex OR commodities", page_size: int = 5) -> List[Dict[str, str]]:
    api_key = os.environ.get("NEWSAPI_API_KEY", "").strip()
    if api_key:
        params = {
            "q": query,
            "pageSize": page_size,
            "sortBy": "publishedAt",
            "language": "en",
            "apiKey": api_key,
        }
        try:
            response = requests.get(NEWSAPI_URL, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            if data.get("status") == "ok":
                return [
                    {
                        "source": article.get("source", {}).get("name", "Unknown"),
                        "title": article.get("title", ""),
                        "url": article.get("url", ""),
                        "published_at": article.get("publishedAt", ""),
                    }
                    for article in data.get("articles", [])[:page_size]
                ]
        except Exception:
            pass

    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    return [
        {
            "source": "TrendIQ Sample",
            "title": "Global markets eye macro risk drivers and liquidity flows.",
            "url": "",
            "published_at": (today - timedelta(hours=2)).isoformat() + "Z",
        },
        {
            "source": "TrendIQ Sample",
            "title": "Economic calendar highlights US CPI, ECB rate outlook, and China PMI.",
            "url": "",
            "published_at": (today - timedelta(hours=5)).isoformat() + "Z",
        },
    ]


def get_economic_calendar(days: int = 7) -> List[Dict[str, str]]:
    now = datetime.utcnow()
    events = [
        {
            "date": (now + timedelta(days=1)).strftime("%Y-%m-%d %H:%M UTC"),
            "event": "US Nonfarm Payrolls",
            "impact": "High",
            "estimate": "TBD",
        },
        {
            "date": (now + timedelta(days=2)).strftime("%Y-%m-%d %H:%M UTC"),
            "event": "Eurozone CPI",
            "impact": "Medium",
            "estimate": "TBD",
        },
        {
            "date": (now + timedelta(days=3)).strftime("%Y-%m-%d %H:%M UTC"),
            "event": "FOMC Minutes",
            "impact": "High",
            "estimate": "TBD",
        },
    ]
    return events
