"""news_sources.py — where headlines come from (2026-07-28).

THE PROBLEM THIS SOLVES
-----------------------
The system had exactly one news source: a per-company Google News RSS query.
Measured over the 548 headlines it had stored, 50% of everything reaching the
score came from scanx.trade and TradingView — a filings restater and a metric
page generator. Not because those were chosen, but because a name-keyed
Google query returns whoever writes about that name most often, and what
machines write most often is auto-generated pages.

So this module adds a second, structurally different channel: a nightly sweep
of the MARKET SECTIONS of real newspapers, archived, then matched against the
universe. Eleven fetches a night buy tier-1 coverage of all 651 names, versus
651 fetches for the same thing per-company. It is the same design that already
works for NSE filings in announcements_fetch.py — fetch a firehose once,
persist it, query the archive per company — and it inverts the source mix,
because a market-section feed contains no metric pages at all.

WHAT WAS TESTED AND REJECTED (2026-07-28, all probed live before building)
--------------------------------------------------------------------------
GDELT 2.0 doc API   returned HTTP 429 on every attempt from this machine.
                    It is free and needs no key, but it rate-limits hard by
                    IP and a GitHub Actions runner shares a datacenter IP,
                    which can only be worse. Implemented below but OFF by
                    default: turn it on only if it starts answering.
BSE announcements   api.bseindia.com/.../AnnGetData answers 200 with
                    "No Record Found!" for every date tried. The NSE feed we
                    already archive covers the same corporate actions for
                    dual-listed names, so this is not worth more probing.
Business Standard   markets RSS is 403 to a plain client.

Everything degrades independently: one dead feed is one missing source, never
a failed scan.
"""

from __future__ import annotations

import csv
import os
import re
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime

from config import NEWSQ

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARCHIVE_PATH = os.path.join(ROOT, "news_archive.csv")
# shared with scoring/news_nlp.py through config — one list, no drift
_WEAK_SOLO = {t.lower() for t in NEWSQ.weak_solo_tokens}
ARCHIVE_FIELDS = ["date", "title", "source", "link"]

_UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

# Market/company sections of outlets that employ reporters. Every one of
# these was fetched successfully on 2026-07-28; the ones that failed are
# named in the module docstring rather than left here to fail nightly.
MARKET_FEEDS: list[tuple[str, str]] = [
    ("The Economic Times", "https://economictimes.indiatimes.com/markets/stocks/rssfeeds/2146842.cms"),
    ("The Economic Times", "https://economictimes.indiatimes.com/industry/rssfeeds/13352306.cms"),
    ("The Economic Times", "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms"),
    ("Moneycontrol", "https://www.moneycontrol.com/rss/business.xml"),
    ("Moneycontrol", "https://www.moneycontrol.com/rss/results.xml"),
    ("Moneycontrol", "https://www.moneycontrol.com/rss/marketreports.xml"),
    ("Livemint", "https://www.livemint.com/rss/markets"),
    ("Livemint", "https://www.livemint.com/rss/companies"),
    ("NDTV Profit", "https://feeds.feedburner.com/ndtvprofit-latest"),
    ("BusinessLine", "https://www.thehindubusinessline.com/markets/feeder/default.rss"),
]

# A hanging publisher must not stall the nightly scan. Ten feeds at a 20s
# socket timeout is 200s worst case; this caps the whole sweep well under that
# and reports which feeds were skipped rather than dropping them silently.
SWEEP_BUDGET_S = 90.0

GDELT_ENABLED = False       # see docstring: 429s on every probe
_GDELT = ("https://api.gdeltproject.org/api/v2/doc/doc?query={q}"
          "&mode=artlist&format=json&maxrecords=25&timespan={days}d")

_GOOGLE = "https://news.google.com/rss/search?q={query}&hl=en-IN&gl=IN&ceid=IN:en"


def _ascii(s: str) -> str:
    """Windows consoles here are cp1252 and these strings reach print(),
    daily_alerts.md and Telegram (the 2026-07-06 lesson)."""
    return (s or "").encode("ascii", "replace").decode("ascii")


def _parse_date(raw: str | None):
    if not raw:
        return None
    try:
        d = parsedate_to_datetime(raw)
    except (TypeError, ValueError):
        return None
    return d.replace(tzinfo=None) if d and d.tzinfo else d


def _fetch_rss(url: str, timeout: int = 20) -> list[dict]:
    req = urllib.request.Request(url, headers=_UA)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        root = ET.fromstring(resp.read())
    out = []
    for item in root.iter("item"):
        title = _ascii(item.findtext("title") or "").strip()
        if not title:
            continue
        out.append({
            "title": title,
            "date": _parse_date(item.findtext("pubDate")),
            "link": (item.findtext("link") or "").strip(),
            "source": _ascii(item.findtext("source") or "").strip(),
        })
    return out


# ---------------------------------------------------------------------------
# the nightly sweep
# ---------------------------------------------------------------------------

def _dedup_key(link: str, title: str) -> str:
    """Identity of an article across re-publication.

    Raw links carry tracking parameters (?utm_source=, #comments, session
    ids), so the same story re-archives every night under a new URL and the
    file grows without gaining anything. Strip the query and fragment; fall
    back to a normalised title when there is no link at all."""
    if link:
        base = link.split("#")[0].split("?")[0].rstrip("/")
        if base:
            return base.lower()
    return re.sub(r"[^a-z0-9]", "", (title or "").lower())[:80]


def _prune(rows: list[dict], retention_days: int) -> tuple[list[dict], int]:
    cutoff = datetime.now() - timedelta(days=retention_days)
    kept = []
    for r in rows:
        try:
            d = datetime.fromisoformat(r["date"])
        except (ValueError, KeyError):
            kept.append(r)          # undated: keep, never silently discard
            continue
        if d.tzinfo:
            d = d.replace(tzinfo=None)
        if d >= cutoff:
            kept.append(r)
    return kept, len(rows) - len(kept)


def sweep_market_feeds(verbose: bool = True) -> dict:
    """Fetch every market feed, append new items, prune old ones.

    Returns a health dict rather than a bare count, because "0 new headlines"
    means one thing when every feed answered and something entirely different
    when none did — and the caller cannot tell those apart from a number.

    A feed that 403s or times out costs its own coverage and nothing else.
    The whole sweep is bounded by SWEEP_BUDGET_S so a hanging publisher
    cannot stall the nightly scan."""
    existing: list[dict] = []
    seen: set[str] = set()
    if os.path.exists(ARCHIVE_PATH):
        with open(ARCHIVE_PATH, encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                existing.append(row)
                seen.add(_dedup_key(row.get("link", ""), row.get("title", "")))

    started = time.monotonic()
    rows, failed, skipped = [], [], []
    for source, url in MARKET_FEEDS:
        if time.monotonic() - started > SWEEP_BUDGET_S:
            skipped.append(source)
            continue
        try:
            items = _fetch_rss(url)
        except Exception as e:                    # noqa: BLE001 — per-feed isolation
            failed.append(f"{source}: {type(e).__name__}")
            if verbose:
                print(f"  news feed failed ({source}): {type(e).__name__} {str(e)[:60]}")
            continue
        for it in items:
            key = _dedup_key(it["link"], it["title"])
            if key in seen:
                continue
            seen.add(key)
            rows.append({"date": (it["date"] or datetime.now()).isoformat(timespec="seconds"),
                         "title": it["title"], "source": it["source"] or source,
                         "link": it["link"]})

    # Rewrite rather than append so the file stays bounded. This archive is
    # committed on every cloud run, and git stores a whole new blob each time
    # a file changes, so an unbounded CSV is an unbounded repository.
    merged, dropped = _prune(existing + rows, NEWSQ.archive_retention_days)
    if rows or dropped:
        with open(ARCHIVE_PATH, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=ARCHIVE_FIELDS)
            w.writeheader()
            w.writerows(merged)
    _invalidate_cache()

    ok = len(MARKET_FEEDS) - len(failed) - len(skipped)
    health = {"new": len(rows), "kept": len(merged), "pruned": dropped,
              "feeds_ok": ok, "feeds_total": len(MARKET_FEEDS),
              "failed": failed, "skipped": skipped,
              "all_failed": ok == 0}
    if verbose:
        print(f"  news archive: +{health['new']} headlines from "
              f"{ok}/{len(MARKET_FEEDS)} feeds"
              + (f", pruned {dropped} past {NEWSQ.archive_retention_days}d" if dropped else "")
              + (f", {len(skipped)} skipped on time budget" if skipped else ""))
    return health


def archived_headlines(days: int = 30) -> list[dict]:
    """Everything in the archive inside the window, newest first."""
    if not os.path.exists(ARCHIVE_PATH):
        return []
    cutoff = datetime.now() - timedelta(days=days)
    out = []
    with open(ARCHIVE_PATH, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            try:
                d = datetime.fromisoformat(row["date"])
            except (ValueError, KeyError):
                continue
            if d.tzinfo:
                d = d.replace(tzinfo=None)
            if d < cutoff:
                continue
            out.append({"text": row.get("title", ""), "date": d,
                        "source": row.get("source", ""), "link": row.get("link", "")})
    out.sort(key=lambda x: x["date"], reverse=True)
    return out


_ARCHIVE_CACHE: list[dict] | None = None


def _invalidate_cache() -> None:
    """The archive is read once per process and reused across the several
    names a scan enriches. The sweep runs before enrichment today, but that
    ordering is not enforced anywhere — if it ever flips, a stale cache would
    hide the night's own headlines from the night's own cards. Cheap to be
    correct regardless of call order."""
    global _ARCHIVE_CACHE
    _ARCHIVE_CACHE = None


def archived_for(tokens: list[str], days: int = 30, limit: int = 12) -> list[dict]:
    """Archived headlines naming a company, by its distinctive tokens.

    The archive is read once per process and reused: a nightly scan enriches
    several names against the same ~20,000-row file."""
    global _ARCHIVE_CACHE
    if _ARCHIVE_CACHE is None:
        _ARCHIVE_CACHE = archived_headlines(days=max(days, 90))
    if not tokens:
        return []
    cutoff = datetime.now() - timedelta(days=days)
    if len(tokens) == 1:
        # A one-word name only matches if the word is long enough to be its
        # own identity. Building a prefix pattern here regardless of length
        # made C.E. Info Systems (whose distinctive token is just "info")
        # match every headline containing "Infosys".
        tok = tokens[0]
        if len(tok) < 6 or tok.lower() in _WEAK_SOLO:
            return []
        rx = re.compile(r"\b" + re.escape(tok) + r"\w*", re.I)
    else:
        rx = re.compile(r"\b" + r"\W+".join(re.escape(t) for t in tokens[:2]) + r"\w*", re.I)
    out = []
    for it in _ARCHIVE_CACHE:
        if it["date"] < cutoff:
            continue
        if rx.search(it["text"]):
            out.append(it)
        if len(out) >= limit:
            break
    return out


# ---------------------------------------------------------------------------
# per-company sources
# ---------------------------------------------------------------------------

def google_news(company_name: str, days: int = 30, limit: int = 20) -> list[dict]:
    """The original source, unchanged in spirit: a name-keyed Google News
    query. Kept because it reaches trade press and regional outlets no market
    feed carries — its weakness was never coverage, it was that nothing
    downstream judged what came back."""
    name = company_name
    for suffix in (" Ltd.", " Ltd", " Limited", " LIMITED"):
        if name.endswith(suffix):
            name = name[: -len(suffix)]
    url = _GOOGLE.format(query=urllib.parse.quote(f'"{name}"'))
    items = _fetch_rss(url)
    cutoff = datetime.now() - timedelta(days=days)
    out = []
    for it in items:
        d = it["date"]
        if d is None or d < cutoff:
            continue
        out.append({"text": it["title"], "date": d,
                    "source": it["source"], "link": it["link"]})
    out.sort(key=lambda x: x["date"], reverse=True)
    return out[:limit]


def gdelt(company_name: str, days: int = 30, limit: int = 20) -> list[dict]:
    """Opt-in. Free and keyless, but rate-limited to the point of being
    unusable from this machine — see the module docstring."""
    if not GDELT_ENABLED:
        return []
    import json
    url = _GDELT.format(q=urllib.parse.quote(f'"{company_name}"'), days=int(days))
    req = urllib.request.Request(url, headers=_UA)
    with urllib.request.urlopen(req, timeout=25) as resp:
        payload = json.loads(resp.read().decode("utf-8", "replace"))
    out = []
    for a in (payload.get("articles") or [])[:limit]:
        try:
            d = datetime.strptime(a.get("seendate", ""), "%Y%m%dT%H%M%SZ")
        except ValueError:
            d = None
        out.append({"text": _ascii(a.get("title", "")), "date": d,
                    "source": a.get("domain", ""), "link": a.get("url", "")})
    return [o for o in out if o["text"]]


def collect(company_name: str, tokens: list[str], days: int = 30,
            health: dict | None = None) -> list[dict]:
    """Every source, merged and de-duplicated by link then by title.

    Each source is independently non-fatal: the whole point of having three
    is that a dead one degrades coverage rather than the scan.

    But swallowing every exception made a TOTAL outage indistinguishable from
    a quiet news day — both produced an empty list and a card reading "no
    news", which is a confident statement the system had no right to make.
    Pass a dict as `health` to receive what actually happened per source; the
    caller decides whether "nothing found" is a fact or a failure."""
    items: list[dict] = []
    errors: dict[str, str] = {}
    counts: dict[str, int] = {}
    sources = [("google", lambda: google_news(company_name, days)),
               ("archive", lambda: archived_for(tokens, days))]
    if GDELT_ENABLED:
        sources.append(("gdelt", lambda: gdelt(company_name, days)))

    for label, fn in sources:
        try:
            got = fn()
        except Exception as e:                     # noqa: BLE001
            errors[label] = f"{type(e).__name__}: {str(e)[:60]}"
            continue
        counts[label] = len(got)
        for it in got:
            it.setdefault("via", label)
        items.extend(got)

    if health is not None:
        health.update({
            "counts": counts, "errors": errors,
            "sources_tried": len(sources), "sources_ok": len(counts),
            # every live source raised: we know nothing, rather than knowing
            # there is nothing
            "blind": len(counts) == 0,
        })

    seen_link: set[str] = set()
    seen_title: set[str] = set()
    out = []
    for it in sorted(items, key=lambda x: x["date"] or datetime.min, reverse=True):
        link = (it.get("link") or "").split("?")[0]
        norm = re.sub(r"[^a-z0-9]", "", (it.get("text") or "").lower())[:70]
        if (link and link in seen_link) or (norm and norm in seen_title):
            continue
        if link:
            seen_link.add(link)
        if norm:
            seen_title.add(norm)
        out.append(it)
    return out


if __name__ == "__main__":     # python -m data.news_sources
    n, failed = sweep_market_feeds()
    arch = archived_headlines(days=30)
    print(f"archive now holds {len(arch)} headlines in the last 30d "
          f"({failed} feed(s) failed this run)")
