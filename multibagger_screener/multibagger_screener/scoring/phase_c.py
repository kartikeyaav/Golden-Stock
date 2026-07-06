"""
phase_c.py — LIVE-ONLY news/theme/catalyst enrichment for alert candidates
(brief section 2B item 4: enrichment context for the human, never a machine
gate; no historical corpus exists, so weights are earned via the journal).

Reuses the v1 news_catalyst govt-theme scoring, adds dated-event catalyst
detection and a governance red-flag scan over recent headlines. Lights up
conviction dimensions 3 (theme_tailwind) and 6 (catalyst) on the card.
"""

from __future__ import annotations

from datetime import datetime, timezone

from config import CATALYST
from data.announcements_fetch import announcements_for, archived_for
from data.news_catalyst import score_catalyst, tag_government_themes
from data.news_fetch import fetch_headlines
from scoring.conviction import Dimension


def _keyword_hits(text: str, keywords: list[str]) -> list[str]:
    t = text.lower()
    return [k for k in keywords if k.lower() in t]


def enrich(symbol: str, company_name: str) -> dict:
    """Fetch + score recent news for one company. Never raises — a network
    failure returns {'ok': False} and the card just says 'news unavailable'."""
    try:
        headlines = fetch_headlines(company_name, days=int(CATALYST.news_recency_days))
    except Exception as e:  # noqa: BLE001 — enrichment must never kill a scan
        return {"ok": False, "error": str(e)[:100]}

    now = datetime.now(timezone.utc)
    items = [{"date": h["date"], "text": h["text"], "source": h["source"]}
             for h in headlines]

    # official NSE filings: live rolling feed UNION our own 7-day archive
    # (the archive survives the feed's short memory) — scanned with the same
    # keyword sets but listed separately and trusted more
    try:
        live = announcements_for(company_name)
    except Exception:  # noqa: BLE001 — feed down != scan down
        live = []
    try:
        old = archived_for(company_name, days=7)
    except Exception:  # noqa: BLE001
        old = []
    seen_subjects = set()
    filings = []
    for f in live + old:
        key = f["subject"][:80]
        if key not in seen_subjects:
            seen_subjects.add(key)
            filings.append(f)

    theme_hits: set[str] = set()
    event_hits: set[str] = set()
    red_flags: list[str] = []
    for h in headlines:
        theme_hits.update(tag_government_themes(h["text"]))
        event_hits.update(_keyword_hits(h["text"], CATALYST.catalyst_event_keywords))
        for flag in _keyword_hits(h["text"], CATALYST.red_flag_keywords):
            red_flags.append(f"'{flag}' in: {h['text'][:90]}")
    for f in filings:
        theme_hits.update(tag_government_themes(f["subject"]))
        event_hits.update(_keyword_hits(f["subject"], CATALYST.catalyst_event_keywords))
        for flag in _keyword_hits(f["subject"], CATALYST.red_flag_keywords):
            red_flags.append(f"[NSE FILING] '{flag}': {f['subject'][:90]}")

    # dimension 6 (catalyst): dated events + v1 recency/volume blend
    base = score_catalyst(items, as_of=now)          # govt-theme weighted 0-1
    event_component = min(len(event_hits) / 3.0, 1.0)
    catalyst_score = round(min(1.0, 0.5 * event_component + 0.5 * base
                               + (0.1 if len(items) >= 5 else 0.0)), 3)

    # dimension 3 (theme): explicit govt/structural theme mentions
    theme_score = round(min(1.0, 0.3 + 0.35 * min(len(theme_hits), 2)), 3) \
        if theme_hits else 0.3

    return {
        "ok": True,
        "headline_count": len(headlines),
        "headlines": headlines[:5],
        "filings": filings[:5],
        "themes": sorted(theme_hits),
        "events": sorted(event_hits),
        "red_flags": red_flags[:5],
        "catalyst_score": catalyst_score,
        "theme_score": theme_score,
    }


def enrichment_dimensions(e: dict) -> list[Dimension]:
    """Conviction dimensions from an enrich() result (v0, news-based —
    the notes say so; journal data decides whether these earn more weight)."""
    if not e.get("ok"):
        return []
    cat_notes = (f"{e['headline_count']} headlines/30d; events: "
                 f"{', '.join(e['events']) if e['events'] else 'none'}")
    theme_notes = (f"themes: {', '.join(e['themes'])}" if e["themes"]
                   else "no govt/structural theme detected in headlines")
    return [
        Dimension("catalyst", e["catalyst_score"], cat_notes + " (news-based v0)"),
        Dimension("theme_tailwind", e["theme_score"], theme_notes + " (news-based v0)"),
    ]
