"""test_gap_universe.py — the coverage-gap cohort (PREREG_2026-09-07).

Adopted 2026-09-07 after a backtest showed the 377-name band lifts CAGR
19.63 -> 21.66% and shallows max drawdown 21.13 -> 18.60%. Traded ALONE the
same names return 7.14%, so the gain is diversification, not stock-picking —
which is why the cohort must stay LABELLED and SEPARABLE forever. A merge that
loses the label destroys the ability to ever answer "was this a good idea?"

Run:  python -m pytest tests/test_gap_universe.py -q
"""

from __future__ import annotations

import os
import subprocess

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAP = os.path.join(ROOT, "gap_universe.csv")
UNI = os.path.join(ROOT, "universe.csv")


def test_gap_cohort_file_exists_and_is_labelled():
    g = pd.read_csv(GAP)
    assert len(g) > 0
    assert set(g["index_source"]) == {"nse_gap"}, "the cohort must carry ONE label"
    assert g["symbol"].is_unique


def test_gap_universe_is_tracked_by_git():
    """THE PERSISTENCE TRAP. If this file were gitignored the cloud checkout
    would not have it, build_universe would print its 'absent' note, produce a
    650-name universe that looks perfectly normal — and the weekly would then
    COMMIT that, silently reverting the adoption. Five instances of 'a file the
    pipeline needs does not exist in production' are already in this repo's
    history; this is the cheap guard against a sixth."""
    r = subprocess.run(["git", "ls-files", "--error-unmatch",
                        "multibagger_screener/multibagger_screener/gap_universe.csv"],
                       capture_output=True, text=True,
                       cwd=os.path.abspath(os.path.join(ROOT, "..", "..")))
    assert r.returncode == 0, "gap_universe.csv is NOT tracked by git — the cloud will not have it"


def test_universe_contains_the_cohort_and_keeps_the_index_names():
    u = pd.read_csv(UNI)
    g = pd.read_csv(GAP)
    assert list(u.columns) == ["symbol", "company", "industry", "index_source"], \
        "universe.csv schema changed — every downstream reader assumes these four"
    gap_rows = u[u["index_source"] == "nse_gap"]
    assert len(gap_rows) > 0, "the cohort is not in universe.csv"
    for src, n in (("midcap150", 150), ("smallcap250", 250), ("microcap250", 250)):
        assert (u["index_source"] == src).sum() == n, f"{src} should still be {n}"
    assert u["symbol"].is_unique


def test_an_index_name_never_gets_the_gap_label():
    """If a gap name is promoted into an index at rebalance it must be labelled
    by the index, or the forward record credits the experiment with an index
    name's trades. build_universe concats indices FIRST and keeps the first
    duplicate, which is what enforces this."""
    u = pd.read_csv(UNI)
    idx = set(u.loc[u["index_source"] != "nse_gap", "symbol"])
    gap = set(u.loc[u["index_source"] == "nse_gap", "symbol"])
    assert not (idx & gap), f"labelled both ways: {sorted(idx & gap)[:5]}"


def test_every_gap_name_is_sized_and_exitable():
    """Absent mcap or turnover must EXCLUDE, never admit. This codebase's
    signature bug is absent data granting a privilege; the band gate refuses
    anything it cannot size or verify it can exit."""
    g = pd.read_csv(GAP)
    assert g["market_cap_cr_at_add"].notna().all()
    assert g["turnover_cr_at_add"].notna().all()
    assert (g["market_cap_cr_at_add"] >= 1000).all()
    assert (g["market_cap_cr_at_add"] <= 25000).all()
    assert (g["turnover_cr_at_add"] >= 1.0).all()


def test_blank_industry_is_scored_not_renormalised_away():
    """The cohort has no NSE macro-industry, and theme_tailwind is a 15-point
    conviction dimension. If a themeless name returned None the weight would
    renormalise AWAY and every gap name would float up — the exact failure that
    put 22 junk names in the penny top-13 in July. It returns 0.3 (a score, a
    mild penalty) and this test is what keeps it that way."""
    import sys
    sys.path.insert(0, ROOT)
    from scoring.phase_c import _theme_read
    score, names, note, keys = _theme_read("ZZZNOTREAL", "Nonexistent Holdings Limited", "")
    assert score is not None, \
        "a themeless name now returns None — its 15-point weight will renormalise away"
    assert 0.0 <= score < 0.5, f"expected a low SCORE, got {score}"
    assert names == [] and keys == []


def test_gap_signals_never_enter_the_capital_gate_cohort():
    """CAPITAL_GATE.md was registered 2026-07-26 to judge the entries the
    BACKTEST VALIDATED. The nse_gap cohort is an experiment justified by a
    survivor-biased backtest that is explicitly not confirmation, and it has
    its own forward test (PREREG_2026-09-07.md §4). Letting its signals into
    the gate would change the population a real-capital decision is measured
    on, mid-flight. Amendment logged in CAPITAL_GATE.md §9."""
    import sys
    sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, "scripts"))
    from gate_status import split_cohorts

    gap_sym = pd.read_csv(GAP)["symbol"].iloc[0]
    idx_sym = pd.read_csv(UNI).query("index_source != 'nse_gap'")["symbol"].iloc[0]
    rows = pd.DataFrame([
        {"symbol": idx_sym, "kind": "BUY TRIGGER", "logged_at": "2026-08-01 10:00",
         "plan_followed_R": 1.0},
        {"symbol": gap_sym, "kind": "BUY TRIGGER", "logged_at": "2026-08-01 10:00",
         "plan_followed_R": 9.0},
    ])
    parts = split_cohorts(rows)
    assert gap_sym not in set(parts["gate"]["symbol"]), \
        f"{gap_sym} (nse_gap) leaked into the capital-gate cohort"
    assert idx_sym in set(parts["gate"]["symbol"]), \
        "the exclusion is over-broad — it dropped an index name too"
    assert gap_sym not in set(parts["legacy"]["symbol"]), \
        "gap signals leaked into the legacy cohort, which is also reported"
    assert gap_sym in set(parts["gap"]["symbol"]), \
        "gap signals must still be TRACKED, just counted toward nothing here"
