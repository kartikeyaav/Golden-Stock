"""test_watchdog_session.py — the freshness watchdog must judge the scan on the
SESSION it read and the PRICES it saw, not on when it last ran.

WHY (2026-09-12). The watchdog existed through the whole 09-08 outage and said
nothing for the first day and a half. Its scan check read `tags_state.date`,
the day the scan last ran, with a 2-day limit. On 09-08 two runs COMPLETED with
1,027 of 1,028 names still on the previous session's close — a fresh date on
stale content — and every run after that crashed outright. A stamp that only
answers "did something run recently" cannot tell a working pipeline from a
broken one, and this is the test that pins the difference.

Case 2 below is the exact state the old rule called healthy.

CANARIED 2026-09-12: run against the previous scan_watchdog.py, case 2 and
case 6 are not late, i.e. the old check passed the outage.

Run:  python -m pytest tests/test_watchdog_session.py -q
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from scan_watchdog import expected_session, scan_row  # noqa: E402

UTC = timezone.utc


def _state(ran, session, coverage):
    out = {}
    if ran is not None:
        out["date"] = ran.isoformat()
    if session is not None:
        out["session"] = session.isoformat()
    if coverage is not None:
        out["price_coverage"] = coverage
    return out


# ---------------------------------------------------------------------------
# which session should already be in the record
# ---------------------------------------------------------------------------

def test_expected_session_walks_back_over_the_weekend_and_the_grace_window():
    # the watchdog's own slot: Tuesday 01:30 UTC -> Monday's session
    assert expected_session(datetime(2026, 9, 8, 1, 30, tzinfo=UTC)) == \
        datetime(2026, 9, 7).date()
    # Saturday 01:30 UTC -> Friday
    assert expected_session(datetime(2026, 9, 12, 1, 30, tzinfo=UTC)) == \
        datetime(2026, 9, 11).date()
    # Monday 01:30 UTC -> the previous Friday, never the weekend
    assert expected_session(datetime(2026, 9, 7, 1, 30, tzinfo=UTC)) == \
        datetime(2026, 9, 4).date()
    # a LATE delivery at midday must not demand a session whose slots have
    # not run yet — GitHub delivered this watchdog 4.5h late on 09-10
    assert expected_session(datetime(2026, 9, 9, 12, 0, tzinfo=UTC)) == \
        datetime(2026, 9, 8).date()
    # by late evening, today's session is fairly expected
    assert expected_session(datetime(2026, 9, 9, 20, 0, tzinfo=UTC)) == \
        datetime(2026, 9, 9).date()


# ---------------------------------------------------------------------------
# the six states the scan can be in
# ---------------------------------------------------------------------------

NOW = datetime(2026, 9, 9, 1, 30, tzinfo=UTC)      # Wednesday 01:30 UTC
WANT = expected_session(NOW)                        # Tuesday 2026-09-08


def test_1_a_healthy_scan_is_quiet():
    r = scan_row(NOW, _state(WANT, WANT, 0.99))
    assert not r["late"], r


def test_2_the_hollow_run_that_fooled_the_old_check_is_late():
    """09-08, verbatim: it RAN, it stamped today, it saw no prices."""
    r = scan_row(NOW, _state(WANT, WANT, 0.001))
    assert r["late"], r
    assert "coverage" in r["detail"]
    assert "price refresh is failing" in r["why"], r["why"]


def test_3_a_crashing_scan_is_late():
    r = scan_row(NOW, _state(WANT - timedelta(days=2), WANT - timedelta(days=2), 0.99))
    assert r["late"], r
    assert "no scan has run since" in r["why"], r["why"]


def test_4_missing_state_is_late_not_forgiven():
    """Absent data must never buy a job a night off — the recurring shape in
    this repo, and the reason this assertion exists at all."""
    r = scan_row(NOW, {})
    assert r["late"], r
    assert "never run" in r["why"] or "never" in r["detail"]


def test_5_a_market_holiday_is_not_an_alarm():
    """On a holiday the scan runs, finds every name on the same older bar, and
    coverage stays 1.0. Only the session stands still — which must NOT page
    anyone, or the watchdog gets muted and stops working entirely."""
    r = scan_row(NOW, _state(WANT, WANT - timedelta(days=1), 1.0))
    assert not r["late"], r


def test_6_a_feed_that_never_moves_is_late_even_though_the_scan_runs():
    """The blind spot left by the other two tests: a scan that runs every
    night, reports full coverage, and reads the same fortnight-old bar."""
    r = scan_row(NOW, _state(WANT, WANT - timedelta(days=14), 1.0))
    assert r["late"], r
    assert "price feed has stopped" in r["why"], r["why"]


if __name__ == "__main__":
    failures = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"ok   {name}")
            except Exception as e:  # noqa: BLE001
                failures += 1
                print(f"FAIL {name}: {type(e).__name__}: {str(e)[:200]}")
    print(f"\n{failures} failure(s)")
    sys.exit(1 if failures else 0)
