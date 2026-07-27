"""
tests/test_scan_integrity.py — the nightly scan's silent-failure guards.

Every check here exists because the failure it catches is INVISIBLE: the scan
completes, the report reads normally, Telegram says "no transitions", and the
tags underneath were computed on data that never arrived. Autonomous systems
do not fail loudly on their own; these are the places we make them.

    python tests/test_scan_integrity.py
"""

from __future__ import annotations

import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "scripts"))

import daily_scan

FAILS: list[str] = []
_UNDER_PYTEST = "PYTEST_CURRENT_TEST" in os.environ


def check(name: str, cond: bool, detail: str = "") -> None:
    if cond:
        print(f"  ok   {name}")
        return
    FAILS.append(f"{name} — {detail}")
    print(f"  FAIL {name} — {detail}")
    if _UNDER_PYTEST:
        raise AssertionError(f"{name} — {detail}")


def _tags(n: int, tag: str = "WATCH") -> dict:
    return {f"S{i}": tag for i in range(n)}


def test_partial_refresh_is_loud():
    """The 2026-07-24 shape: most of the universe a session behind, every
    other check passing. This must shout."""
    tags = _tags(100, "CONFIRMED")
    fresh = pd.Timestamp("2026-07-24")
    stale = pd.Timestamp("2026-07-23")
    last_bars = {s: (fresh if i < 10 else stale) for i, s in enumerate(tags)}
    out = daily_scan.health_check(tags, list(tags) + ["NIFTY50"],
                                  last_bars=last_bars)
    hit = [p for p in out if "behind the newest cached bar" in p]
    check("a 90% stale universe raises a health problem", bool(hit), str(out))
    check("the problem names both counts", "90 of 100" in hit[0] if hit else False,
          hit[0] if hit else "")


def test_uniform_cache_is_quiet():
    """A market holiday moves every symbol together — no symbol is behind the
    newest bar, so the check must not false-positive."""
    tags = _tags(100, "CONFIRMED")
    last_bars = {s: pd.Timestamp("2026-07-24") for s in tags}
    out = daily_scan.health_check(tags, list(tags) + ["NIFTY50"],
                                  last_bars=last_bars)
    check("a uniformly-dated cache raises no staleness problem",
          not [p for p in out if "behind the newest" in p], str(out))


def test_a_few_suspended_names_are_tolerated():
    """Genuinely suspended/renamed names always lag. Below the threshold they
    must not drown the report — the per-holding check covers the ones we own."""
    tags = _tags(100, "CONFIRMED")
    last_bars = {s: (pd.Timestamp("2026-07-10") if i < 5
                     else pd.Timestamp("2026-07-24"))
                 for i, s in enumerate(tags)}
    out = daily_scan.health_check(tags, list(tags) + ["NIFTY50"],
                                  last_bars=last_bars)
    check("5% lagging names stay quiet",
          not [p for p in out if "behind the newest" in p], str(out))


def test_dry_run_writes_nothing():
    """--dry-run must gate every persistent write. The journal is append-only:
    a test run that reaches it cannot be undone, only quarantined (2026-07-09)."""
    was = daily_scan.DRY_RUN
    try:
        daily_scan.DRY_RUN = True
        j = daily_scan.JOURNAL_PATH
        before = os.path.getmtime(j) if os.path.exists(j) else None
        daily_scan.journal_append([{"logged_at": "x", "symbol": "FAKE",
                                    "kind": "BUY TRIGGER"}])
        daily_scan.entry_signals_append([{"logged_at": "x", "symbol": "FAKE",
                                          "kind": "BUY TRIGGER"}])
        daily_scan.save_alert_details({"FAKE": {"alerted_at": "2026-07-27"}})
        after = os.path.getmtime(j) if os.path.exists(j) else None
        check("dry run does not touch the signals journal", before == after,
              f"{before} -> {after}")
    finally:
        daily_scan.DRY_RUN = was


def test_news_radar_window_is_not_advanced_by_a_test_run():
    """scan_radar windows from its own last-run stamp, so persisting during a
    test would shorten the REAL run's window and drop a night of filings."""
    from data import news_radar
    import inspect
    sig = inspect.signature(news_radar.scan_radar)
    check("scan_radar takes a persist flag", "persist" in sig.parameters, "")
    check("scan_radar persists by default",
          sig.parameters["persist"].default is True, "")
    from data import news_pressure
    check("news_pressure.scan takes a persist flag",
          "persist" in inspect.signature(news_pressure.scan).parameters, "")


if __name__ == "__main__":
    print("scan integrity")
    test_partial_refresh_is_loud()
    test_uniform_cache_is_quiet()
    test_a_few_suspended_names_are_tolerated()
    test_dry_run_writes_nothing()
    test_news_radar_window_is_not_advanced_by_a_test_run()
    print()
    if FAILS:
        print(f"{len(FAILS)} FAILED:")
        for f in FAILS:
            print("  -", f)
        sys.exit(1)
    print("all scan-integrity checks passed")
