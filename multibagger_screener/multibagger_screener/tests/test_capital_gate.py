"""
tests/test_capital_gate.py — the gate's judgement, locked.

This is the file that decides whether real money moves, so the behaviours
worth protecting are the ones that would let a bad cohort look good:

  * the legacy pre-fix alerts must never enter the gate cohort
  * VALIDATED (EXTENDED) must never enter it either (the live system skips
    those entries, so they cannot judge it)
  * unsized signals must not be averaged into the expectancy
  * an open winner must not be counted before it is closed or aged
  * every pass condition must actually be able to FAIL

    python tests/test_capital_gate.py
"""

from __future__ import annotations

import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "scripts"))

import gate_status
from config import GATE

FAILS: list[str] = []

# Script mode collects every failure and reports them together at the end;
# pytest needs each check to RAISE or the test function passes no matter what
# it found. Without this the file was decorative under pytest — a deliberately
# false check still reported "7 passed" (found 2026-07-27).
def _under_pytest() -> bool:
    """Evaluated at CALL time, not import time. PYTEST_CURRENT_TEST is set by
    pytest while a test RUNS, not while the module is imported — reading it at
    import time made this whole guard a no-op, which is how a deliberately
    false check still reported "11 passed" (caught by the CI canary
    2026-07-27)."""
    return "PYTEST_CURRENT_TEST" in os.environ or "pytest" in sys.modules


def check(name: str, cond: bool, detail: str = "") -> None:
    if cond:
        print(f"  ok   {name}")
        return
    FAILS.append(f"{name} — {detail}")
    print(f"  FAIL {name} — {detail}")
    if _under_pytest():
        raise AssertionError(f"{name} — {detail}")


def _row(sym, kind, days, r, status="open", sized=True, when="2026-08-01"):
    return {"logged_at": f"{when} 18:40:00", "symbol": sym, "kind": kind,
            "days_elapsed": days, "plan_followed_R": r, "status": status,
            "plan_status": "closed" if status == "stopped" else "open",
            "plan_sized": sized}


def test_cohort_split():
    df = pd.DataFrame([
        _row("AAA", "BUY TRIGGER", 40, 1.0),
        _row("BBB", "EPISODIC PIVOT", 40, 2.0),
        _row("CCC", "BUY CANDIDATE", 40, 5.0, when="2026-07-10"),   # legacy
        _row("DDD", "RE-ENTRY WINDOW", 40, 9.0, when="2026-07-12"),  # legacy
    ])
    parts = gate_status.split_cohorts(df)
    gate_syms = set(parts["gate"]["symbol"])
    check("gate cohort takes only validated entry kinds",
          gate_syms == {"AAA", "BBB"}, f"got {gate_syms}")
    check("legacy cohort keeps the pre-fix alerts",
          set(parts["legacy"]["symbol"]) == {"CCC", "DDD"},
          str(set(parts["legacy"]["symbol"])))
    # the failure this guards: a +9R legacy winner inflating the gate
    stats = gate_status.cohort_stats(parts["gate"])
    check("legacy winners cannot inflate the gate expectancy",
          abs(stats["expectancy_r"] - 1.5) < 1e-6, str(stats["expectancy_r"]))


def test_date_floor():
    df = pd.DataFrame([
        _row("OLD", "BUY TRIGGER", 40, 3.0, when="2026-07-20"),  # before the fix
        _row("NEW", "BUY TRIGGER", 40, 1.0, when="2026-07-28"),
    ])
    parts = gate_status.split_cohorts(df)
    check("signals before the registration date are excluded",
          set(parts["gate"]["symbol"]) == {"NEW"},
          str(set(parts["gate"]["symbol"])))


def test_qualifying_rule():
    df = pd.DataFrame([
        _row("YOUNG", "BUY TRIGGER", 3, 4.0),                 # open, too new
        _row("AGED", "BUY TRIGGER", 45, 1.0),                 # aged in
        _row("STOPPED", "BUY TRIGGER", 2, -1.0, "stopped"),   # closed, counts
    ])
    q = gate_status._qualifying(df)
    check("an open winner younger than the age rule is not banked",
          "YOUNG" not in set(q["symbol"]), str(set(q["symbol"])))
    check("aged and closed signals both qualify",
          {"AGED", "STOPPED"} <= set(q["symbol"]), str(set(q["symbol"])))
    stats = gate_status.cohort_stats(df)
    check("expectancy uses only qualifying signals",
          abs(stats["expectancy_r"] - 0.0) < 1e-6, str(stats["expectancy_r"]))


def test_unsized_excluded():
    df = pd.DataFrame([
        _row("SIZED", "BUY TRIGGER", 40, 1.0),
        _row("WIDE", "BUY TRIGGER", 40, 9.0, sized=False),  # engine refuses it
    ])
    stats = gate_status.cohort_stats(df)
    check("signals the risk engine refuses are not averaged in",
          abs(stats["expectancy_r"] - 1.0) < 1e-6, str(stats["expectancy_r"]))
    check("...but they are still counted and reported",
          stats["n_unsized"] == 1, str(stats["n_unsized"]))


def test_concentration_and_stops():
    # one monster trade carrying an otherwise losing cohort
    rows = [_row(f"L{i}", "BUY TRIGGER", 40, -1.0, "stopped") for i in range(9)]
    rows.append(_row("WIN", "BUY TRIGGER", 40, 30.0))
    stats = gate_status.cohort_stats(pd.DataFrame(rows))
    check("one lottery ticket shows as 100% of positive R",
          stats["best_trade_share_pct"] == 100.0, str(stats["best_trade_share_pct"]))
    check("a cohort that mostly stops out reports a high hit-stop rate",
          stats["hit_stop_pct"] >= GATE.max_hit_stop_pct,
          str(stats["hit_stop_pct"]))


def test_age_matched_bar_scales_with_cohort_age():
    """The 2026-07-27 amendment. The bar must RISE as the cohort ages, because
    the ruler's reading rises with age too — that equivalence is the whole
    point of the change, and a flat bar is what it replaced."""
    young = gate_status.age_matched_reference(pd.Series([30] * 40))
    mid = gate_status.age_matched_reference(pd.Series([90] * 40))
    old = gate_status.age_matched_reference(pd.Series([365] * 40))
    check("the reference rises with cohort age", young < mid < old,
          f"{young} {mid} {old}")
    check("the frozen curve anchors the 30-day point",
          abs(young - GATE.expectancy_curve[0][1]) < 1e-9, str(young))
    check("beyond the last curve point the bar stops extrapolating",
          abs(gate_status.age_matched_reference(pd.Series([3650] * 5)) - old) < 1e-9, "")


def test_amended_bar_admits_what_the_flat_bar_wrongly_rejected():
    """A cohort at +0.40R and 60 days old is running ABOVE half the backtest's
    own 60-day read (+0.679R). The flat +0.50R bar failed it; that was the
    defect."""
    df = pd.DataFrame([_row(f"S{i}", "BUY TRIGGER", 60, 0.40) for i in range(40)])
    s = gate_status.cohort_stats(df)
    check("required bar is half the age-matched reference",
          abs(s["required_expectancy_r"]
              - s["age_matched_reference_r"] * GATE.min_expectancy_fraction) < 1e-6,
          str(s["required_expectancy_r"]))
    check("a cohort beating the age-matched bar passes condition 1",
          s["expectancy_r"] >= s["required_expectancy_r"],
          f"{s['expectancy_r']} vs {s['required_expectancy_r']}")
    check("...and the superseded flat bar would have failed it",
          s["expectancy_r"] < GATE.min_expectancy_r, str(s["expectancy_r"]))


def test_amended_bar_still_fails_a_weak_cohort():
    """The amendment must not become a way to pass anything. Below half the
    age-matched read is still a fail."""
    df = pd.DataFrame([_row(f"S{i}", "BUY TRIGGER", 60, 0.20) for i in range(40)])
    s = gate_status.cohort_stats(df)
    check("a cohort under the age-matched bar fails",
          s["expectancy_r"] < s["required_expectancy_r"],
          f"{s['expectancy_r']} vs {s['required_expectancy_r']}")


def test_frozen_curve_is_not_recomputed_at_evaluation_time():
    """A bar that could drift with a re-run is not pre-registered. The curve
    must come from config, not from whatever the trade files say today."""
    check("curve lives in config", len(GATE.expectancy_curve) >= 4, "")
    check("curve is ordered by age",
          all(GATE.expectancy_curve[i][0] < GATE.expectancy_curve[i + 1][0]
              for i in range(len(GATE.expectancy_curve) - 1)), "")
    check("curve is monotone in R (a later read is never worth less)",
          all(GATE.expectancy_curve[i][1] <= GATE.expectancy_curve[i + 1][1]
              for i in range(len(GATE.expectancy_curve) - 1)), "")
    check("the superseded flat bar is retained for audit",
          GATE.min_expectancy_r == 0.50, str(GATE.min_expectancy_r))


def test_benchmark_window():
    """The benchmark must read a real cached series and respect its window.

    The price cache is gitignored (75MB, regenerable), so on a fresh clone —
    which is exactly what CI checks out — there is no MOMENTUM100 series to
    read. Asserting on it there was failing every CI run since the workflow
    was added, and because `pytest` is the first step, the CANARY step below
    it never ran: the check that proves this suite can detect a failure was
    itself skipped on every push. A permanently red signal is the same as no
    signal.

    So a MISSING cache skips (environment), while a cache that is present and
    reads wrong still fails (real bug). Those are different facts and only
    one of them is about the code.
    """
    b = gate_status.benchmark_return(GATE.benchmark_symbol,
                                     pd.Timestamp("2025-07-01"))
    if b.get("ret_pct") is None and "no cached series" in str(b.get("why", "")):
        msg = (f"{GATE.benchmark_symbol} not in the local price cache — "
               f"window assertions need a real series; run scripts/fetch_data.py")
        print(f"  skip {msg}")
        if _under_pytest():
            import pytest
            pytest.skip(msg)
        return
    check("momentum benchmark series is cached and readable",
          b.get("ret_pct") is not None, str(b))
    if b.get("ret_pct") is not None:
        check("benchmark window starts on or after the requested date",
              b["from"] >= "2025-07-01", b.get("from", "?"))
        short = gate_status.benchmark_return(GATE.benchmark_symbol,
                                             pd.Timestamp("2099-01-01"))
        check("a window with no sessions returns None, not a fake zero",
              short.get("ret_pct") is None, str(short))


def test_live_evaluate():
    """The real evaluation must run end to end and never claim a decision it
    cannot support."""
    g = gate_status.evaluate()
    check("verdict is one of the three legal values",
          g["verdict"] in ("ACCRUING", "PASSED", "FAILED"), g["verdict"])
    if g["cohort"]["n_qualifying"] < GATE.min_signals:
        check("an undersized sample can never read PASSED",
              g["verdict"] != "PASSED", g["verdict"])
        check("the sample condition reports itself as unmet",
              g["conditions"]["sample"]["ok"] is False, "")
    check("the pre-registered thresholds are carried in the payload",
          g["required"]["min_expectancy_fraction"] == GATE.min_expectancy_fraction, "")
    check("the superseded flat bar stays in the payload for audit",
          g["required"]["superseded_flat_min_expectancy_r"] == GATE.min_expectancy_r, "")
    check("the frozen reference curve is carried in the payload",
          len(g["required"]["expectancy_curve"]) == len(GATE.expectancy_curve), "")
    check("legacy cohort is reported separately from the gate",
          "legacy" in g and "cohort" in g, "")


if __name__ == "__main__":
    print("capital gate")
    test_cohort_split()
    test_date_floor()
    test_qualifying_rule()
    test_unsized_excluded()
    test_concentration_and_stops()
    test_age_matched_bar_scales_with_cohort_age()
    test_amended_bar_admits_what_the_flat_bar_wrongly_rejected()
    test_amended_bar_still_fails_a_weak_cohort()
    test_frozen_curve_is_not_recomputed_at_evaluation_time()
    test_benchmark_window()
    test_live_evaluate()
    print()
    if FAILS:
        print(f"{len(FAILS)} FAILED:")
        for f in FAILS:
            print("  -", f)
        sys.exit(1)
    print("all capital-gate checks passed")
