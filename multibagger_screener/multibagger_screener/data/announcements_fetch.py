"""
announcements_fetch.py — official NSE corporate announcements via NSE's own
RSS feed (nsearchives). FIRST-PARTY filings — order wins, results notices,
pledge disclosures, auditor/board changes — unlike Google News headlines,
these can't be someone else's paraphrase and can't false-positive on an
unrelated story.

The feed is a rolling window of the most recent ~400 filings (about the last
trading day), which matches the daily-scan cadence: each evening scan sees
that day's filings. Fetched ONCE per process and cached (the daily scan may
enrich several names).
"""

from __future__ import annotations

import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime

_UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
_FEED_URL = "https://nsearchives.nseindia.com/content/RSS/Online_announcements.xml"

_FEED_CACHE: list[dict] | None = None


def _ascii(s: str) -> str:
    return s.encode("ascii", "replace").decode("ascii")


def _normalize_company(name: str) -> str:
    n = name.lower().strip()
    for suffix in (" limited", " ltd.", " ltd"):
        if n.endswith(suffix):
            n = n[: -len(suffix)]
    return n.strip(" .")


def fetch_announcements(force: bool = False) -> list[dict]:
    """The full current feed: [{company, subject, date, link}] newest first."""
    global _FEED_CACHE
    if _FEED_CACHE is not None and not force:
        return _FEED_CACHE

    req = urllib.request.Request(_FEED_URL, headers=_UA)
    with urllib.request.urlopen(req, timeout=30) as resp:
        root = ET.fromstring(resp.read())

    items = []
    for it in root.iter("item"):
        title = (it.findtext("title") or "").strip()
        desc = (it.findtext("description") or "").strip()
        pub = (it.findtext("pubDate") or "").strip()
        try:
            date = datetime.strptime(pub, "%d-%b-%Y %H:%M:%S")
        except ValueError:
            date = None
        items.append({
            "company": _ascii(title),
            "company_norm": _normalize_company(title),
            "subject": _ascii(desc),
            "date": date,
            "link": (it.findtext("link") or "").strip(),
        })
    _FEED_CACHE = items
    return items


def announcements_for(company_name: str) -> list[dict]:
    """Filings in the current feed matching one company (normalized name)."""
    target = _normalize_company(company_name)
    if not target:
        return []
    return [a for a in fetch_announcements()
            if a["company_norm"] == target
            or a["company_norm"].startswith(target)
            or target.startswith(a["company_norm"])]
