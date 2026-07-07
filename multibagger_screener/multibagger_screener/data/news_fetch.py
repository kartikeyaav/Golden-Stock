"""
news_fetch.py — recent headlines for one company via Google News RSS.
Stdlib only (urllib + xml.etree), no API key, free.

Used ONLY for live enrichment of alert candidates (1-3 names/day) — never
batch-scored across the universe (cost + noise), never a machine gate
(brief section 2B). Failures degrade gracefully to "no news data".

Quality controls (2026-07-07, from user feedback):
  RELEVANCE  the headline must actually name the company (a distinctive token
             of the name appears in the title) — kills the "GST office in
             Chennai" false match on Chennai Petroleum.
  TRUST      each item is tagged trusted/untrusted by source; only trusted
             items feed the catalyst/theme scores, untrusted are shown but
             flagged and score-excluded.
  SENTIMENT  a v0 keyword sentiment (+1/0/-1) per headline so the card can
             show a net read (clearly labelled v0 — not real NLP).
"""

from __future__ import annotations

import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

from config import CATALYST

_UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
_RSS = "https://news.google.com/rss/search?q={query}&hl=en-IN&gl=IN&ceid=IN:en"


def _ascii(s: str) -> str:
    """cp1252 console safety — headlines carry rupee signs, smart quotes..."""
    return s.encode("ascii", "replace").decode("ascii")


def _name_tokens(company_name: str) -> list[str]:
    """Distinctive words of the company name (drop generic corp boilerplate)."""
    generic = set(CATALYST.generic_name_words)
    words = re.findall(r"[a-z0-9]+", company_name.lower())
    toks = [w for w in words if len(w) > 2 and w not in generic]
    return toks or words  # never return empty


def _is_relevant(title: str, tokens: list[str]) -> bool:
    """Relevant if the headline contains the full distinctive name OR at least
    two distinctive tokens (one common word like 'Chennai' isn't enough)."""
    t = title.lower()
    full = " ".join(tokens)
    if full and full in t:
        return True
    hits = sum(1 for tok in tokens if re.search(rf"\b{re.escape(tok)}", t))
    return hits >= 2 if len(tokens) >= 2 else hits >= 1


def _is_trusted(source: str) -> bool:
    s = source.lower()
    return any(src in s for src in CATALYST.trusted_sources)


def _sentiment(title: str) -> int:
    t = title.lower()
    pos = sum(1 for w in CATALYST.positive_words if w in t)
    neg = sum(1 for w in CATALYST.negative_words if w in t)
    return (pos > neg) - (neg > pos)  # +1 / 0 / -1


def fetch_headlines(company_name: str, days: int = 30, limit: int = 15) -> list[dict]:
    """Recent, RELEVANT headlines newest first, each tagged with source trust
    and a v0 sentiment. Query is the company name minus boilerplate suffixes."""
    name = company_name
    for suffix in (" Ltd.", " Ltd", " Limited", " LIMITED"):
        if name.endswith(suffix):
            name = name[: -len(suffix)]
    tokens = _name_tokens(name)
    query = urllib.parse.quote(f'"{name}"')

    req = urllib.request.Request(_RSS.format(query=query), headers=_UA)
    with urllib.request.urlopen(req, timeout=20) as resp:
        root = ET.fromstring(resp.read())

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    items = []
    for item in root.iter("item"):
        title = _ascii(item.findtext("title") or "")
        pub = item.findtext("pubDate")
        source = _ascii(item.findtext("source") or "")
        link = item.findtext("link") or ""
        try:
            date = parsedate_to_datetime(pub) if pub else None
        except (TypeError, ValueError):
            date = None
        if date is None or date < cutoff:
            continue
        if not _is_relevant(title, tokens):
            continue  # drop unrelated stories (the false-match fix)
        items.append({"date": date, "text": title, "source": source, "link": link,
                      "trusted": _is_trusted(source), "sentiment": _sentiment(title)})

    items.sort(key=lambda x: x["date"], reverse=True)
    return items[:limit]
