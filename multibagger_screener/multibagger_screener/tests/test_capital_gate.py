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


def check(name: str, cond: bool, detail: str = "") -> None:
    if cond:
        print(f"  ok   {name}")
    else:
        FAILS.append(f"{name} — {detail}")
        print(f"  FAIL {name} — {detail}")


def _row(sym, kind, days, r, status="open", sized=True, when="2026-08-01"):
    return {"logged_at": f"{when} 18:40:00", "symbol": sym, "kind": kind,
            "days_elapsed": days, "plan_followed_R": r, "status": status,
            "plan_status": "closed" if status == "stopped" else "open",
            "plan_sized": sized}


def test_cohort_split(monkey_status):
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


def test_benchmark_window():
    """The benchmark must read a real cached series and respect its window."""
    b = gate_status.benchmark_return(GATE.benchmark_symbol,
                                     pd.Timestamp("2025-07-01"))
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
          g["required"]["min_expectancy_r"] == GATE.min_expectancy_r, "")
    check("legacy cohort is reported separately from the gate",
          "legacy" in g and "cohort" in g, "")


if __name__ == "__main__":
    print("capital gate")
    test_cohort_split(None)
    test_date_floor()
    test_qualifying_rule()
    test_unsized_excluded()
    test_concentration_and_stops()
    test_benchmark_window()
    test_live_evaluate()
    print()
    if FAILS:
        print(f"{len(FAILS)} FAILED:")
        for f in FAILS:
            print("  -", f)
        sys.exit(1)
    print("all capital-gate checks passed")
