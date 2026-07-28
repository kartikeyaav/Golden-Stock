"""test_news_sources.py — the fetch layer's failure modes.

These are robustness tests, not accuracy tests: they cover what happens when
publishers go down, when the same article is republished under a tracking URL,
and when the archive grows without bound. Network is never touched — every
source is monkeypatched.

Run:  python -m pytest tests/test_news_sources.py -q
"""

from __future__ import annotations

import csv
import os
import sys
from datetime import datetime, timedelta

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from config import NEWSQ  # noqa: E402
from data import news_sources as S  # noqa: E402


# ---------------------------------------------------------------------------
# de-duplication
# ---------------------------------------------------------------------------

def test_tracking_parameters_do_not_re_archive_the_same_article():
    """The same story arrives nightly with a fresh utm_source. Keying on the
    raw link grew the archive forever without adding information."""
    a = S._dedup_key("https://x.com/story-1?utm_source=rss&utm_medium=feed", "T")
    b = S._dedup_key("https://x.com/story-1?utm_source=twitter", "T")
    c = S._dedup_key("https://x.com/story-1#comments", "T")
    assert a == b == c


def test_linkless_items_fall_back_to_the_title():
    a = S._dedup_key("", "Karur Vysya Bank Q1 profit rises 45%")
    b = S._dedup_key("", "karur vysya bank q1 profit rises 45%!")
    assert a == b and a != ""


def test_different_stories_stay_distinct():
    assert S._dedup_key("https://x.com/a", "A") != S._dedup_key("https://x.com/b", "B")


# ---------------------------------------------------------------------------
# retention
# ---------------------------------------------------------------------------

def test_prune_drops_only_what_is_past_the_window():
    now = datetime.now()
    rows = [{"date": (now - timedelta(days=d)).isoformat(), "title": f"t{d}"}
            for d in (1, 30, 119, 121, 400)]
    kept, dropped = S._prune(rows, 120)
    assert dropped == 2
    assert [r["title"] for r in kept] == ["t1", "t30", "t119"]


def test_prune_keeps_undated_rows_rather_than_silently_discarding_them():
    rows = [{"date": "", "title": "undated"},
            {"date": "not-a-date", "title": "junk"}]
    kept, dropped = S._prune(rows, 120)
    assert dropped == 0 and len(kept) == 2


def test_retention_is_wider_than_every_consumer_window():
    """news_pressure reads 90 days. If retention ever drops below what a
    consumer reads, the consumer silently loses history."""
    from config import NEWS
    assert NEWSQ.archive_retention_days > NEWS.lookback_days


# ---------------------------------------------------------------------------
# sweep health: silence is not success
# ---------------------------------------------------------------------------

def _fake_feed(items):
    return lambda url, timeout=20: list(items)


def test_sweep_reports_total_failure_distinctly(tmp_path, monkeypatch):
    """Every feed down is not 'a quiet night' — the caller must be able to
    tell those apart, because one is a fact about the market and the other is
    a fact about our plumbing."""
    monkeypatch.setattr(S, "ARCHIVE_PATH", str(tmp_path / "news.csv"))
    monkeypatch.setattr(S, "_fetch_rss",
                        lambda url, timeout=20: (_ for _ in ()).throw(OSError("down")))
    h = S.sweep_market_feeds(verbose=False)
    assert h["all_failed"] is True
    assert h["feeds_ok"] == 0
    assert len(h["failed"]) == len(S.MARKET_FEEDS)


def test_sweep_partial_failure_is_not_total_failure(tmp_path, monkeypatch):
    monkeypatch.setattr(S, "ARCHIVE_PATH", str(tmp_path / "news.csv"))
    calls = {"n": 0}

    def flaky(url, timeout=20):
        calls["n"] += 1
        if calls["n"] % 2:
            raise OSError("down")
        return [{"title": f"Story {calls['n']}", "date": datetime.now(),
                 "link": f"https://x.com/{calls['n']}", "source": "ET"}]

    monkeypatch.setattr(S, "_fetch_rss", flaky)
    h = S.sweep_market_feeds(verbose=False)
    assert h["all_failed"] is False
    assert 0 < h["feeds_ok"] < h["feeds_total"]
    assert h["new"] > 0


def test_sweep_prunes_and_rewrites_rather_than_growing_forever(tmp_path, monkeypatch):
    path = tmp_path / "news.csv"
    old = (datetime.now() - timedelta(days=400)).isoformat(timespec="seconds")
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=S.ARCHIVE_FIELDS)
        w.writeheader()
        w.writerow({"date": old, "title": "ancient", "source": "ET", "link": "https://x/o"})
    monkeypatch.setattr(S, "ARCHIVE_PATH", str(path))
    monkeypatch.setattr(S, "_fetch_rss", _fake_feed([
        {"title": "Fresh", "date": datetime.now(), "link": "https://x/n", "source": "ET"}]))
    h = S.sweep_market_feeds(verbose=False)
    assert h["pruned"] == 1
    titles = [r["title"] for r in csv.DictReader(open(path, encoding="utf-8"))]
    assert "ancient" not in titles and "Fresh" in titles


def test_sweep_invalidates_the_read_cache(tmp_path, monkeypatch):
    """The cache is process-global. If the sweep did not clear it, a scan that
    enriched before sweeping would never see the night's own headlines."""
    monkeypatch.setattr(S, "ARCHIVE_PATH", str(tmp_path / "news.csv"))
    monkeypatch.setattr(S, "_fetch_rss", _fake_feed([]))
    S._ARCHIVE_CACHE = [{"text": "stale", "date": datetime.now(),
                         "source": "", "link": ""}]
    S.sweep_market_feeds(verbose=False)
    assert S._ARCHIVE_CACHE is None


# ---------------------------------------------------------------------------
# collect(): a blind read must announce itself
# ---------------------------------------------------------------------------

def test_collect_flags_a_total_outage_as_blind(monkeypatch):
    monkeypatch.setattr(S, "google_news",
                        lambda *a, **k: (_ for _ in ()).throw(OSError("dns")))
    monkeypatch.setattr(S, "archived_for",
                        lambda *a, **k: (_ for _ in ()).throw(OSError("disk")))
    health: dict = {}
    out = S.collect("Some Co Ltd.", ["some", "co"], health=health)
    assert out == []
    assert health["blind"] is True
    assert set(health["errors"]) == {"google", "archive"}


def test_collect_with_one_source_alive_is_not_blind(monkeypatch):
    monkeypatch.setattr(S, "google_news",
                        lambda *a, **k: (_ for _ in ()).throw(OSError("dns")))
    monkeypatch.setattr(S, "archived_for", lambda *a, **k: [
        {"text": "Some Co bags order", "date": datetime.now(),
         "source": "ET", "link": "https://x/1"}])
    health: dict = {}
    out = S.collect("Some Co Ltd.", ["some", "co"], health=health)
    assert len(out) == 1
    assert health["blind"] is False
    assert health["sources_ok"] == 1


def test_an_empty_but_healthy_read_is_not_blind(monkeypatch):
    """The distinction that matters: we looked and found nothing."""
    monkeypatch.setattr(S, "google_news", lambda *a, **k: [])
    monkeypatch.setattr(S, "archived_for", lambda *a, **k: [])
    health: dict = {}
    assert S.collect("Quiet Co Ltd.", ["quiet"], health=health) == []
    assert health["blind"] is False


# ---------------------------------------------------------------------------
# archive matching
# ---------------------------------------------------------------------------

def test_a_weak_single_token_name_matches_nothing(monkeypatch):
    """"JM Financial" reduces to the token "financial", which matched "Jio
    Financial Services". A one-word name that is a bare industry word cannot
    identify anybody."""
    monkeypatch.setattr(S, "_ARCHIVE_CACHE", [
        {"text": "Jio Financial Services posts Q1 profit", "date": datetime.now(),
         "source": "ET", "link": "https://x/1"}])
    assert S.archived_for(["financial"]) == []
    assert S.archived_for(["info"]) == []


def test_a_two_token_name_matches_as_a_phrase(monkeypatch):
    monkeypatch.setattr(S, "_ARCHIVE_CACHE", [
        {"text": "Karur Vysya Bank Q1 profit rises 45%", "date": datetime.now(),
         "source": "ET", "link": "https://x/1"},
        {"text": "Some other bank reports results", "date": datetime.now(),
         "source": "ET", "link": "https://x/2"}])
    got = S.archived_for(["karur", "vysya", "bank"])
    assert len(got) == 1 and "Karur" in got[0]["text"]


def test_the_sweep_budget_is_bounded():
    """Ten feeds at a 20s socket timeout is 200s worst case; the nightly scan
    must not be able to stall on a hanging publisher."""
    assert S.SWEEP_BUDGET_S < 20 * len(S.MARKET_FEEDS)
