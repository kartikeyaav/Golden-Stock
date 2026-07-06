"""
news_fetch.py — recent headlines for one company via Google News RSS.
Stdlib only (urllib + xml.etree), no API key, free.

Used ONLY for live enrichment of alert candidates (1-3 names/day) — never
batch-scored across the universe (cost + noise), never a machine gate
(brief section 2B). Failures degrade gracefully to "no news data".
"""

from __future__ import annotations

import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

_UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
_RSS = "https://news.google.com/rss/search?q={query}&hl=en-IN&gl=IN&ceid=IN:en"


def _ascii(s: str) -> str:
    """cp1252 console safety — headlines carry rupee signs, smart quotes..."""
    return s.encode("ascii", "replace").decode("ascii")


def fetch_headlines(company_name: str, days: int = 30, limit: int = 15) -> list[dict]:
    """Recent headlines: [{date: datetime, text, source, link}], newest first.
    Query is the company name minus boilerplate suffixes."""
    name = company_name
    for suffix in (" Ltd.", " Ltd", " Limited", " LIMITED"):
        if name.endswith(suffix):
            name = name[: -len(suffix)]
    query = urllib.parse.quote(f'"{name}"')

    req = urllib.request.Request(_RSS.format(query=query), headers=_UA)
    with urllib.request.urlopen(req, timeout=20) as resp:
        root = ET.fromstring(resp.read())

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    items = []
    for item in root.iter("item"):
        title = item.findtext("title") or ""
        pub = item.findtext("pubDate")
        source = item.findtext("source") or ""
        link = item.findtext("link") or ""
        try:
            date = parsedate_to_datetime(pub) if pub else None
        except (TypeError, ValueError):
            date = None
        if date is None or date < cutoff:
            continue
        items.append({"date": date, "text": _ascii(title),
                      "source": _ascii(source), "link": link})

    items.sort(key=lambda x: x["date"], reverse=True)
    return items[:limit]
