"""test_missing_industry.py — a universe row with no industry must not be able
to kill the nightly scan.

2026-09-07 added 377 `nse_gap` names to universe.csv; none of them carries an
NSE industry, so the field arrives as NaN. NaN is a float (`industry.lower()`
raises) and NaN is truthy (`if not industry` and `(industry or "")` both let it
through). The first gap name to fire a buy alert killed the scan, and since all
six catch-up slots replay the same code, the scan stayed dead for 18 runs
across four sessions (09-08 .. 09-11) while Actions showed a red X nobody was
watching.

Two independent guarantees are pinned here, because either one alone would
have turned this outage into a footnote:

  1. every text-reading scorer accepts a missing industry, and
  2. one broken name cannot take the whole run down.

CANARIED 2026-09-12: every assertion below was run against the pre-fix code
and seen RED before the fix was written.

Run:  python -m pytest tests/test_missing_industry.py -q
"""

from __future__ import annotations

import os
import sys

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from scoring import phase_b, phase_c  # noqa: E402
from scoring.pit_fundamentals import PITFundamentals  # noqa: E402
from scoring.textnorm import as_text  # noqa: E402
from scoring.themes import THEMES  # noqa: E402

NAN = float("nan")
# every shape a missing industry actually arrives in: pandas NaN from a blank
# CSV cell, an absent dict key, and the whitespace a hand-edited file leaves
MISSING = [None, NAN, "", "   "]


def test_as_text_turns_every_absence_into_an_empty_string():
    for v in MISSING:
        assert as_text(v) == "", repr(v)
    assert as_text(" Cables ") == "Cables"
    # the printed forms of missing values must not survive as real text
    for junk in ("nan", "NaN", "None", "<NA>", "NaT"):
        assert as_text(junk) == "", junk


def test_is_financial_accepts_a_missing_industry():
    for v in MISSING:
        assert phase_b._is_financial(v) is False, repr(v)
    assert phase_b._is_financial("Financial Services") is True
    assert phase_b._is_financial("Private Sector Bank") is True
    assert phase_b._is_financial("Cables") is False


def test_archetypes_accept_a_missing_industry():
    row = {"np_latest_q": 10, "np_yoy_q": -5, "opm_latest_q": 12, "opm_yoy_q": 4}
    for v in MISSING:
        assert isinstance(phase_b.tag_archetypes(row, v), list), repr(v)


def test_theme_matching_accepts_a_missing_industry():
    for t in THEMES:
        for v in MISSING:
            assert t.matches("ZZZTEST", "Zzz Transmission & Cables Ltd", v) in (True, False)


def test_theme_read_accepts_a_missing_industry():
    for v in MISSING:
        score, names, note, keys = phase_c._theme_read("ZZZTEST", "Zzz Industries Ltd", v)
        assert isinstance(names, list) and isinstance(keys, list)
        assert score is None or 0.0 <= score <= 1.0


def test_pit_fundamentals_accepts_a_missing_industry():
    for v in MISSING:
        assert PITFundamentals("ZZZTEST", v).is_financial is False, repr(v)


def test_every_industry_value_in_the_live_universe_is_scoreable():
    """The data contract, read off the real file rather than a fixture.

    A fixture would have passed all through the outage: the defect was in the
    DATA the universe started carrying, not in any value a test author would
    have thought to write down."""
    u = pd.read_csv(os.path.join(ROOT, "universe.csv"))
    values = list(u["industry"].drop_duplicates())
    assert any(as_text(v) == "" for v in values), (
        "universe.csv no longer has a single blank industry — if the gap "
        "cohort was dropped, this guard has quietly stopped testing anything")
    for v in values:
        phase_b._is_financial(v)
        phase_b.tag_archetypes({}, v)
        for t in THEMES:
            t.matches("ZZZTEST", "Zzz Ltd", v)


def test_one_bad_name_cannot_kill_the_scan():
    """The outage was not that a card failed. It was that a card failure took
    down the other ~1,000 names, the journal, the dashboard and the digest."""
    import daily_scan

    original = daily_scan.build_candidate

    def boom(*a, **k):
        raise AttributeError("'float' object has no attribute 'lower'")

    daily_scan.build_candidate = boom
    try:
        cand = daily_scan.safe_build_candidate(
            "ZZZTEST", {"tag": "CONFIRMED", "last_close": 100.0}, NAN, 80.0,
            company_name="Zzz Ltd")
    finally:
        daily_scan.build_candidate = original

    assert "card" in cand and "detail" in cand
    assert "ZZZTEST" in cand["card"]
    assert cand["detail"].get("card_failed"), "the failure must be recorded, not swallowed"
    # the fallback must not invent journal columns
    assert set(cand) == {"card", "detail"}, sorted(cand)


if __name__ == "__main__":
    failures = 0
    for name, fn in sorted(list(globals().items())):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"ok   {name}")
            except Exception as e:  # noqa: BLE001
                failures += 1
                print(f"FAIL {name}: {type(e).__name__}: {str(e)[:200]}")
    print(f"\n{failures} failure(s)")
    sys.exit(1 if failures else 0)
