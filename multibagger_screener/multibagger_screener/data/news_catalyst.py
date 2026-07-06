"""
news_catalyst.py — tag candidates with thematic/catalyst signals: government
policy tailwinds, recent news volume, analyst commentary, order-book news.

HONEST LIMITATION: this sandbox can't reach news sites, NSE announcements,
or PIB press releases directly (no live internet in the code environment
this was built in). This module is written to run wherever you actually
execute it (your machine / Claude Code, with real internet access), pulling
from whatever news source you wire in — Google News RSS, NSE/BSE corporate
announcement feeds, a paid news API, or simply text you paste in from
reading recent articles/concall transcripts yourself.

The scoring logic (keyword tagging + recency weighting) is real and usable;
only the fetch step is left as an integration point.
"""

from __future__ import annotations

from datetime import datetime
from typing import Iterable

import pandas as pd

from config import CATALYST


def tag_government_themes(text: str, keywords: Iterable[str] | None = None) -> list[str]:
    """Return which government/thematic tailwind keywords appear in a blob of
    text (news article, concall transcript, annual report MD&A section)."""
    keywords = keywords or CATALYST.govt_theme_keywords
    text_lower = text.lower()
    return [kw for kw in keywords if kw.lower() in text_lower]


def score_catalyst(
    news_items: list[dict],
    as_of: datetime | None = None,
) -> float:
    """news_items: list of {"date": datetime, "text": str, "source": str}.
    Produces a 0-1 catalyst score blending:
      - how many distinct government/thematic keywords appear
      - how recent the most relevant mention is
      - simple news volume (more coverage = more market attention, for
        better or worse — treat this as a magnitude signal, not a
        direction signal; pair with sentiment if you have it)
    """
    as_of = as_of or datetime.today()
    if not news_items:
        return 0.0

    theme_hits = set()
    most_recent_relevant_days = None

    for item in news_items:
        hits = tag_government_themes(item["text"])
        if hits:
            theme_hits.update(hits)
            age_days = (as_of - item["date"]).days
            if most_recent_relevant_days is None or age_days < most_recent_relevant_days:
                most_recent_relevant_days = age_days

    if not theme_hits:
        return 0.0

    theme_breadth_score = min(len(theme_hits) / 3.0, 1.0)  # saturates at 3+ distinct themes

    if most_recent_relevant_days is None:
        recency_score = 0.0
    else:
        recency_score = max(0.0, 1.0 - most_recent_relevant_days / (CATALYST.news_recency_days * 2))

    volume_score = min(len(news_items) / 10.0, 1.0)  # saturates at 10+ articles

    return round(0.5 * theme_breadth_score + 0.3 * recency_score + 0.2 * volume_score, 4)


def build_catalyst_table(candidates_news: dict[str, list[dict]]) -> pd.DataFrame:
    """candidates_news: {company_name: [news_items...]}. Returns a DataFrame
    with name, catalyst_score, and the specific themes flagged (for the
    human-readable "why it was selected" writeup)."""
    rows = []
    for name, items in candidates_news.items():
        score = score_catalyst(items)
        all_themes = set()
        for item in items:
            all_themes.update(tag_government_themes(item["text"]))
        rows.append({
            "name": name,
            "catalyst_score": score,
            "themes_flagged": ", ".join(sorted(all_themes)) if all_themes else "",
            "news_count": len(items),
        })
    return pd.DataFrame(rows)
