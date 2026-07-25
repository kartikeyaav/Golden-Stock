"""
tests/test_themes.py — cross-industry theme membership and heat (2026-07-26).

Two classes of defect this locks down, both found against the real 651-name
universe while building the map:

1. GREEDY PATTERNS. r"\\bhealthcare\\b" is the NSE INDUSTRY string, so it pulled
   all 63 pharma names into a hospitals-and-diagnostics theme; r"\\blabs?\\b"
   then pulled in Alkem/Ipca/Laurus LABORATORIES, which are drug makers. A
   theme that swallows a whole industry is worse than no theme, because it
   still looks specific.

2. COMPRESSED HEAT. An absolute 0-100 scale put every theme between 33 and 41
   — arithmetically true (the whole tape moves together) and useless for the
   one job the number has, which is ordering a reading queue. Heat is now a
   rank across themes, and thin themes are excluded from the ranking rather
   than competing on a two-name median.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scoring.themes import (  # noqa: E402
    MIN_MEMBERS_FOR_RANK, THEME_BY_KEY, THEMES, membership, rank_heat, summarize)


def _row(sym, company, ind, tag="WATCH", rs=50):
    return {"sym": sym, "company": company, "ind": ind, "tag": tag, "rs": rs}


def test_seed_symbol_wins_over_its_nse_industry():
    """Apollo Micro Systems files under Capital Goods and is defence."""
    rows = [_row("APOLLO", "Apollo Micro Systems Ltd.", "Capital Goods")]
    m = membership(rows)
    assert "APOLLO" in m["defelec"]


def test_healthcare_industry_does_not_swallow_pharma_into_hospitals():
    rows = [_row("ALKEM", "Alkem Laboratories Ltd.", "Healthcare"),
            _row("IPCALAB", "Ipca Laboratories Ltd.", "Healthcare"),
            _row("LAURUSLABS", "Laurus Labs Ltd.", "Healthcare"),
            _row("FORTIS", "Fortis Healthcare Ltd.", "Healthcare"),
            _row("LALPATHLAB", "Dr. Lal Path Labs Ltd.", "Healthcare")]
    hosp = membership(rows)["hospital"]
    assert "ALKEM" not in hosp and "IPCALAB" not in hosp
    assert "FORTIS" in hosp        # explicit seed
    assert "LALPATHLAB" in hosp    # explicit seed


def test_a_stock_may_belong_to_several_themes():
    """MTAR is nuclear AND defence electronics. Forcing one label would be a
    tidier table and a worse map."""
    rows = [_row("MTARTECH", "MTAR Technologies Ltd.", "Capital Goods")]
    m = membership(rows)
    assert "MTARTECH" in m["nuclear"] and "MTARTECH" in m["defelec"]


def test_pattern_match_admits_a_name_with_no_seed():
    """A new listing must join without a code change."""
    rows = [_row("NEWSOL", "Brand New Solar Power Ltd.", "Power")]
    assert "NEWSOL" in membership(rows)["renewables"]


def test_needs_industry_guards_a_generic_word():
    """'engineering' is only trusted inside industrial buckets."""
    rows = [_row("FAKEFIN", "Engineering Finance Ltd.", "Financial Services")]
    assert "FAKEFIN" not in membership(rows)["capex"]


def test_summarize_counts_only_actionable_tags_as_breadth():
    rows_by = {r["sym"]: r for r in [
        _row("A", "A Ltd", "X", tag="CONFIRMED"),
        _row("B", "B Ltd", "X", tag="ANTICIPATION"),
        _row("C", "C Ltd", "X", tag="EXTENDED"),
        _row("D", "D Ltd", "X", tag="WATCH")]}
    s = summarize(rows_by, ["A", "B", "C", "D"])
    assert s["n"] == 4 and s["breadth"] == 50.0
    assert sorted(s["confirmed"]) == ["A", "B"]


def test_thin_themes_are_flagged_and_excluded_from_the_ranking():
    rows_by = {r["sym"]: r for r in [_row("A", "A Ltd", "X"), _row("B", "B Ltd", "X")]}
    thin = summarize(rows_by, ["A", "B"])
    assert thin["thin"] is True
    assert MIN_MEMBERS_FOR_RANK > 2

    fat = [dict(thin, thin=False, n=10, breadth=b, ret3m=r, news_per_name=0.1)
           for b, r in ((10, 5), (50, 20), (30, 12))]
    summaries = fat + [thin]
    rank_heat(summaries)
    assert thin["heat"] == 0.0
    assert max(s["heat"] for s in fat) > min(s["heat"] for s in fat)


def test_heat_spreads_across_the_full_range():
    """The compression bug: an absolute scale put everything in a 8-point band."""
    summaries = [{"thin": False, "n": 10, "breadth": b, "ret3m": r,
                  "news_per_name": p}
                 for b, r, p in ((5, -10, 0.0), (20, 0, 0.2), (35, 8, 0.4),
                                 (50, 20, 0.8), (60, 30, 1.2))]
    rank_heat(summaries)
    heats = sorted(s["heat"] for s in summaries)
    assert heats[0] == 0.0 and heats[-1] == 100.0
    assert heats == sorted(heats), "heat must be monotonic in the components"


def test_every_theme_has_a_blurb_and_unique_key():
    keys = [t.key for t in THEMES]
    assert len(keys) == len(set(keys))
    assert len(THEME_BY_KEY) == len(THEMES)
    for t in THEMES:
        assert t.blurb.strip() and t.name.strip()
        assert t.seeds or t.words, f"{t.key} can never match anything"
