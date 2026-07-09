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

import time
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

    # the ~400KB download occasionally truncates mid-stream, which surfaces
    # as an XML parse error and would lose that day's filings for good (the
    # feed is a rolling ~1-day window) — retry before giving up (2026-07-09)
    root = None
    for attempt in range(3):
        req = urllib.request.Request(_FEED_URL, headers=_UA)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                root = ET.fromstring(resp.read())
            break
        except (ET.ParseError, OSError):
            if attempt == 2:
                raise
            time.sleep(3)

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


# ---------------------------------------------------------------------------
# Archive: the feed is a rolling ~1-day window — persist it daily so the
# system builds its own filings history instead of forgetting.
# ---------------------------------------------------------------------------
import csv
import os

_ARCHIVE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                             "announcements_archive.csv")
_ARCHIVE_FIELDS = ["date", "company", "company_norm", "subject", "link"]


def archive_feed() -> int:
    """Append today's feed items to the archive (deduped by link+subject).
    Returns the number of NEW rows. Called by the daily scan."""
    items = fetch_announcements()
    seen: set[str] = set()
    if os.path.exists(_ARCHIVE_PATH):
        with open(_ARCHIVE_PATH, "r", encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                seen.add(row.get("link") or row.get("subject", ""))
    new_rows = [a for a in items if (a["link"] or a["subject"]) not in seen]
    if new_rows:
        write_header = not os.path.exists(_ARCHIVE_PATH)
        with open(_ARCHIVE_PATH, "a", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=_ARCHIVE_FIELDS)
            if write_header:
                w.writeheader()
            for a in new_rows:
                w.writerow({"date": a["date"].isoformat(timespec="seconds") if a["date"] else "",
                            "company": a["company"], "company_norm": a["company_norm"],
                            "subject": a["subject"], "link": a["link"]})
    return len(new_rows)


def archived_for(company_name: str, days: int = 7) -> list[dict]:
    """Archived filings for one company over the trailing window — survives
    the live feed's short memory."""
    if not os.path.exists(_ARCHIVE_PATH):
        return []
    target = _normalize_company(company_name)
    cutoff = datetime.now().timestamp() - days * 86400
    out = []
    with open(_ARCHIVE_PATH, "r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            norm = row.get("company_norm", "")
            if not (norm == target or norm.startswith(target) or target.startswith(norm)):
                continue
            try:
                d = datetime.fromisoformat(row["date"])
            except (ValueError, KeyError):
                continue
            if d.timestamp() >= cutoff:
                out.append({"company": row["company"], "subject": row["subject"],
                            "date": d, "link": row["link"]})
    out.sort(key=lambda x: x["date"], reverse=True)
    return out
