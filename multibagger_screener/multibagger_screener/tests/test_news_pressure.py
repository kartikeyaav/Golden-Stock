"""
tests/test_news_pressure.py — story dedupe and decay (2026-07-26).

The defect this locks down is a MEASUREMENT one, found before the feature
shipped rather than after. The obvious implementation of "has this stock been
in the news for a while?" counts filings — and on the real archive that ranks
companies by paperwork volume, not by news. GABRIEL topped the raw count with
nine hits, which were one acquisition (HL Klemove) plus the preferential issue
funding it, filed nine times over four days.

So: same company + same event class inside NEWS.story_gap_days is ONE story,
dated at its first filing, and decay is measured from that first date — the
day the market learned, not the day the last PDF landed.

No network and no archive file: rows are injected directly.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import NEWS                              # noqa: E402
from data import news_pressure as np_                # noqa: E402

NOW = datetime(2026, 7, 26, 9, 0, 0)
UNI = {"gabriel india": "GABRIEL", "acme widgets": "ACMEW"}


def _install_rows(monkey_rows):
    """Replace the archive reader with a fixed list of (date, name, subject)."""
    np_._read_archive = lambda since: sorted(
        [r for r in monkey_rows if since is None or r[0] >= since],
        key=lambda r: r[0])


def _stories(rows):
    _install_rows(rows)
    return np_.build_stories(NOW, UNI)


def test_repeat_filings_of_one_event_collapse_to_one_story():
    """The GABRIEL case: nine filings, one acquisition."""
    rows = [(datetime(2026, 7, 21, 10, 0), "gabriel india",
             "Gabriel India Limited has informed the Exchange about Acquisition of shares in HL Klemove"),
            (datetime(2026, 7, 21, 15, 0), "gabriel india",
             "Gabriel India Limited has informed the Exchange about Acquisition of 4,81,34,427 equity shares"),
            (datetime(2026, 7, 22, 9, 0), "gabriel india",
             "Gabriel India Limited has informed the Exchange regarding Acquisition (including agreement to acquire)"),
            (datetime(2026, 7, 22, 11, 0), "gabriel india",
             "Gabriel India Limited has informed the Exchange regarding Joint venture agreements")]
    st = _stories(rows)
    assert len(st) == 1, f"expected 1 story, got {len(st)}"
    assert st[0].n_filings == 4
    assert st[0].first == datetime(2026, 7, 21, 10, 0)


def test_same_event_beyond_the_gap_is_a_genuinely_new_story():
    """Two order wins six weeks apart are two pieces of news, not one."""
    far = timedelta(days=NEWS.story_gap_days + 30)
    rows = [(datetime(2026, 6, 1, 10, 0), "acme widgets",
             "Acme Widgets Limited receives order worth Rs 500 crore"),
            (datetime(2026, 6, 1, 10, 0) + far, "acme widgets",
             "Acme Widgets Limited receives order worth Rs 800 crore")]
    st = _stories(rows)
    assert len(st) == 2


def test_different_event_classes_stay_separate():
    rows = [(datetime(2026, 7, 21, 10, 0), "gabriel india",
             "Gabriel India Limited has informed the Exchange about Acquisition of shares"),
            (datetime(2026, 7, 21, 12, 0), "gabriel india",
             "Gabriel India Limited has informed the Exchange about Preferential issue")]
    st = _stories(rows)
    assert {s.event for s in st} == {"M&A/JV", "fund raise"}


def test_decay_is_measured_from_when_the_story_broke():
    """A story that ran for a week is aged from its FIRST day, so a company
    re-filing the same event cannot keep refreshing its own pressure."""
    old = [(NOW - timedelta(days=NEWS.half_life_days), "acme widgets",
            "Acme Widgets Limited receives order worth Rs 500 crore")]
    fresh = [(NOW - timedelta(hours=2), "acme widgets",
              "Acme Widgets Limited receives order worth Rs 500 crore")]
    p_old = np_.compute(_stories(old), NOW)["ACMEW"].pressure
    p_new = np_.compute(_stories(fresh), NOW)["ACMEW"].pressure
    assert abs(p_old / p_new - 0.5) < 0.05, "one half-life should halve pressure"


def test_negative_flow_is_never_netted_against_positive():
    """A company can have both. Netting would hide the risk behind the story."""
    rows = [(NOW - timedelta(days=1), "acme widgets",
             "Acme Widgets Limited receives order worth Rs 500 crore"),
            (NOW - timedelta(days=1), "acme widgets",
             "Acme Widgets Limited — SEBI show cause notice received")]
    r = np_.compute(_stories(rows), NOW)["ACMEW"]
    assert r.pressure > 0 and r.risk_pressure > 0
    assert r.n_pos == 1 and r.n_neg == 1


def test_primed_needs_both_story_count_and_pressure():
    """One big story is not a trend; the label must mean accumulated flow."""
    one = [(NOW - timedelta(days=1), "acme widgets",
            "Acme Widgets Limited receives order worth Rs 500 crore")]
    assert np_.compute(_stories(one), NOW)["ACMEW"].primed is False

    two = one + [(NOW - timedelta(days=9), "acme widgets",
                  "Acme Widgets Limited announces capacity expansion at its new plant")]
    r = np_.compute(_stories(two), NOW)["ACMEW"]
    assert r.n_pos == 2 and r.primed is True


def test_summary_reads_as_developments_not_filings():
    rows = [(NOW - timedelta(days=1), "acme widgets",
             "Acme Widgets Limited receives order worth Rs 500 crore"),
            (NOW - timedelta(days=9), "acme widgets",
             "Acme Widgets Limited announces capacity expansion at its new plant")]
    s = np_.compute(_stories(rows), NOW)["ACMEW"].summary()
    assert "2 positive developments" in s
    assert "order win" in s and "expansion" in s
    assert s.isascii(), "card/Telegram text must survive a cp1252 console"


def test_missing_archive_is_not_fatal():
    """A fresh clone has no memory; every consumer must see 'no news'."""
    _install_rows([])
    assert np_.compute(np_.build_stories(NOW, UNI), NOW) == {}
