"""
scripts/gate_status.py — where the system stands against the PRE-REGISTERED
real-capital gate (CAPITAL_GATE.md, machine-readable in `config.GATE`).

    python scripts/gate_status.py            # print + write state/gate.json

This is the only number that decides anything. Everything else on the
dashboard is context for it: the alerts are inputs, the AI layers are
curation, the penny screen and the theme map are research. This file answers
the one question the project exists to answer — *is the machine earning the
right to real money?* — and it answers it against thresholds fixed on
2026-07-26, before the cohort it judges existed.

THREE POPULATIONS, never averaged together:

  GATE COHORT   BUY TRIGGER + EPISODIC PIVOT alerts from 2026-07-25 on: the
                entries the backtest actually validated. Judged on
                plan_followed_R. This is the record.

  LEGACY        the 150 transition-day BUY CANDIDATE / RE-ENTRY WINDOW alerts
                from 2026-07-07 to 2026-07-24, of which ZERO were VALIDATED
                (audit F1: the scan only fired on tag transitions, and only
                27% of validated entries land on one). Real, honest, kept
                visible — and NOT the strategy that was backtested. Reported
                separately, never folded in.

  EXCLUDED      VALIDATED (EXTENDED) — the backtest took these, the live
                system deliberately skips them (F1b), so they cannot judge
                it — and unsized signals (2.5xATR wider than the 12% cap),
                which the live engine refuses to trade. Both are measured and
                shown, because the divergence is the reason the labels exist.

The benchmark is not decoration. Condition 2 of the gate is that a
momentum-quality mid/small-cap ETF — the same factor exposure, one click,
~0.5% a year — must LOSE over the same window. If it wins, the rational
allocation is the ETF.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import GATE, RISK
from data.cache import load_ohlcv

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "state", "gate.json")


def _num(s):
    return pd.to_numeric(s, errors="coerce")


# ---------------------------------------------------------------------------
# benchmarks
# ---------------------------------------------------------------------------
def benchmark_return(symbol: str, start: pd.Timestamp,
                     end: pd.Timestamp | None = None) -> dict:
    """Buy-and-hold % for one cached series over [start, end].

    Uses the first session ON OR AFTER `start` so the comparison begins the
    day the cohort begins, not at some convenient earlier low.
    """
    df = load_ohlcv(symbol)
    if df is None or df.empty:
        return {"sym": symbol, "ret_pct": None, "why": "no cached series"}
    d = df.copy()
    d["date"] = pd.to_datetime(d["date"])
    d = d[d["date"] >= pd.Timestamp(start)]
    if end is not None:
        d = d[d["date"] <= pd.Timestamp(end)]
    if len(d) < 2:
        return {"sym": symbol, "ret_pct": None, "why": "window too short"}
    first, last = float(d["close"].iloc[0]), float(d["close"].iloc[-1])
    return {
        "sym": symbol,
        "ret_pct": round((last / first - 1) * 100, 2),
        "first": round(first, 2), "last": round(last, 2),
        "from": str(d["date"].iloc[0].date()), "to": str(d["date"].iloc[-1].date()),
        "sessions": int(len(d)),
    }


# ---------------------------------------------------------------------------
# cohort selection
# ---------------------------------------------------------------------------
def _entry_status_map() -> dict:
    """symbol+date -> entry_status from journal/entry_signals.csv."""
    p = os.path.join(ROOT, "journal", "entry_signals.csv")
    if not os.path.exists(p):
        return {}
    try:
        es = pd.read_csv(p)
    except (ValueError, OSError):
        return {}
    if es.empty or "entry_status" not in es.columns:
        return {}
    es["logged_at"] = pd.to_datetime(es["logged_at"], errors="coerce")
    out = {}
    for _, r in es.iterrows():
        if pd.isna(r["logged_at"]):
            continue
        out[(str(r["symbol"]), str(r["logged_at"])[:10])] = str(r.get("entry_status", ""))
    return out


def split_cohorts(outcomes: pd.DataFrame) -> dict:
    """Partition journal_outcomes into gate / legacy / extended cohorts."""
    if outcomes is None or outcomes.empty:
        return {"gate": outcomes, "legacy": outcomes, "extended": outcomes}
    df = outcomes.copy()
    df["logged_at"] = pd.to_datetime(df["logged_at"], errors="coerce")
    est = _entry_status_map()
    df["_status_label"] = [
        est.get((str(s), str(d)[:10]), "")
        for s, d in zip(df["symbol"], df["logged_at"])
    ]
    start = pd.Timestamp(GATE.cohort_start_date)
    kind_ok = df["kind"].astype(str).isin(GATE.cohort_kinds)
    status_ok = df["_status_label"].isin(GATE.cohort_entry_status)
    extended = df["_status_label"].astype(str).str.contains("EXTENDED", na=False)
    in_window = df["logged_at"] >= start
    gate = df[in_window & (kind_ok | status_ok) & ~extended]
    return {
        "gate": gate,
        "extended": df[in_window & extended],
        # everything the old scan fired, kept whole and reported apart
        "legacy": df[~(in_window & (kind_ok | status_ok) & ~extended)],
    }


def _qualifying(df: pd.DataFrame) -> pd.DataFrame:
    """Signals eligible to be counted: CLOSED, or aged past min_age_days.

    Without this an open winner could be counted at its peak and a losing
    cohort could be held "still open" forever.
    """
    if df is None or df.empty:
        return df
    d = df.copy()
    age = _num(d.get("days_elapsed"))
    closed = d.get("plan_status", pd.Series(dtype=str)).astype(str).str.lower()
    is_closed = closed.isin(("closed", "stopped", "exited")) | (
        d.get("status", pd.Series(dtype=str)).astype(str) == "stopped")
    return d[is_closed | (age >= GATE.min_age_days)]


def age_matched_reference(ages: pd.Series) -> float | None:
    """What the VALIDATED backtest reads for signals of these ages.

    The gate compares like with like (CAPITAL_GATE.md §4, amended 2026-07-27).
    A 35-day-old live signal is measured against what the backtest's own entries
    were worth 35 days in — not against their full-hold value, which this
    strategy only reaches in the right tail a year later.

    Linear interpolation between the frozen curve points; flat beyond both ends
    (below 30d the gate does not count a signal at all, and past 365d the curve
    is measured on too few entries to extrapolate).
    """
    a = pd.to_numeric(ages, errors="coerce").dropna()
    if a.empty:
        return None
    xs = [p[0] for p in GATE.expectancy_curve]
    ys = [p[1] for p in GATE.expectancy_curve]
    return float(np.interp(a.clip(lower=xs[0], upper=xs[-1]), xs, ys).mean())


def cohort_stats(df: pd.DataFrame, sized_only: bool = True,
                 qualifying_only: bool = True) -> dict:
    """Expectancy and the discipline checks over one cohort.

    `qualifying_only` applies the gate's closed-or-aged rule. It is REQUIRED
    for the gate decision and MISLEADING as a running read: until the journal
    is 30 days deep, "closed" means "stopped out", so the filter selects the
    losers and nothing else. That artifact is exactly why both readings are
    computed and labelled rather than one being quietly chosen.
    """
    if df is None or df.empty:
        return {"n": 0, "n_qualifying": 0, "expectancy_r": None}
    q = _qualifying(df) if qualifying_only else df.copy()
    total_logged = int(len(df))
    if sized_only and "plan_sized" in q.columns:
        # the live engine refuses to size these (stop wider than the 12% cap),
        # so they cannot judge it — counted, reported, not averaged in
        unsized = q[q["plan_sized"].astype(str).str.lower() == "false"]
        q = q[q["plan_sized"].astype(str).str.lower() != "false"]
    else:
        unsized = q.iloc[0:0]
    r = _num(q.get(GATE.ruler)).dropna()
    if r.empty:
        return {"n": total_logged, "n_qualifying": int(len(q)),
                "expectancy_r": None, "n_unsized": int(len(unsized))}
    pos = r[r > 0]
    best_share = (round(float(pos.max() / pos.sum()) * 100, 1)
                  if len(pos) and float(pos.sum()) > 0 else None)
    hit_stop = None
    if "status" in q.columns:
        hit_stop = round(float((q["status"].astype(str) == "stopped").mean()) * 100, 1)
    # what the backtest reads for signals of these same ages — the bar this
    # cohort is actually held to (CAPITAL_GATE.md §4, amended 2026-07-27)
    ref = age_matched_reference(q.loc[r.index].get("days_elapsed", pd.Series(dtype=float)))
    return {
        "n": total_logged,
        "n_qualifying": int(len(r)),
        "n_unsized": int(len(unsized)),
        "expectancy_r": round(float(r.mean()), 3),
        "median_age_days": (int(pd.to_numeric(q.loc[r.index]["days_elapsed"],
                                              errors="coerce").median())
                            if "days_elapsed" in q.columns else None),
        "age_matched_reference_r": round(ref, 3) if ref is not None else None,
        "required_expectancy_r": (round(ref * GATE.min_expectancy_fraction, 3)
                                  if ref is not None else None),
        "median_r": round(float(r.median()), 3),
        "sum_r": round(float(r.sum()), 2),
        "win_rate_pct": round(float((r > 0).mean()) * 100, 1),
        "hit_stop_pct": hit_stop,
        "best_trade_share_pct": best_share,
        "best_r": round(float(r.max()), 2),
        "worst_r": round(float(r.min()), 2),
        # what the cohort would have returned taking EVERY signal at the
        # configured risk. Signal basis, not a portfolio: no slot cap, no
        # compounding, no correlation. Stated in the UI wherever it appears.
        "signal_basis_return_pct": round(float(r.sum()) * RISK.risk_per_trade_pct, 2),
        "first": str(pd.to_datetime(q["logged_at"]).min())[:10] if len(q) else None,
        "last": str(pd.to_datetime(q["logged_at"]).max())[:10] if len(q) else None,
    }


# ---------------------------------------------------------------------------
# the gate itself
# ---------------------------------------------------------------------------
def evaluate() -> dict:
    op = os.path.join(ROOT, "journal", "journal_outcomes.csv")
    outcomes = pd.read_csv(op) if os.path.exists(op) else pd.DataFrame()
    parts = split_cohorts(outcomes)
    gate = cohort_stats(parts["gate"])
    # the running read: every signal so far, marked through the same plan
    # ruler. This is what a human watches week to week; it does NOT decide
    # anything, and the UI labels it as immature until `gate` is decidable.
    gate_running = cohort_stats(parts["gate"], qualifying_only=False)
    # legacy is reported on the running read on purpose — it is the number
    # every other surface quotes (-0.23R), and applying the gate's
    # closed-or-aged rule to a 17-day-old journal would report its stop-outs
    # alone and call it the cohort's expectancy
    legacy = cohort_stats(parts["legacy"], qualifying_only=False)
    extended = cohort_stats(parts["extended"], qualifying_only=False)

    # benchmark window: the cohort's own span, else from registration day, so
    # the comparator can never be quietly given a friendlier window
    start = pd.Timestamp(gate.get("first") or GATE.cohort_start_date)
    bm = benchmark_return(GATE.benchmark_symbol, start)
    bm2 = benchmark_return(GATE.secondary_benchmark_symbol, start)

    # CONTEXT ONLY, never the gate comparison. Until the cohort exists the
    # gate window is empty, and an empty window would leave the comparator
    # invisible — which is how a benchmark quietly stops being checked. These
    # trailing reads keep it on screen. They are computed over fixed lookbacks
    # and are explicitly NOT what condition 2 tests; substituting one for the
    # other would be exactly the window-shopping §8 forbids.
    now = pd.Timestamp.today().normalize()
    context = {}
    for label, days in (("3m", 91), ("12m", 365)):
        context[label] = {
            "bench": benchmark_return(GATE.benchmark_symbol, now - pd.Timedelta(days=days)),
            "bench2": benchmark_return(GATE.secondary_benchmark_symbol,
                                       now - pd.Timedelta(days=days)),
        }

    exp = gate.get("expectancy_r")
    ref = gate.get("age_matched_reference_r")
    req = gate.get("required_expectancy_r")
    sysret = gate.get("signal_basis_return_pct")
    have_n = gate.get("n_qualifying", 0) >= GATE.min_signals

    def _cond(ok, detail):
        return {"ok": bool(ok) if ok is not None else None, "detail": detail}

    conditions = {
        "sample": _cond(
            have_n,
            f"{gate.get('n_qualifying', 0)} of {GATE.min_signals} qualifying signals "
            f"(closed, or aged {GATE.min_age_days}d+)"),
        "expectancy": _cond(
            None if (exp is None or req is None) else exp >= req,
            (f"{exp:+.2f}R vs {req:+.2f}R required — "
             f"{GATE.min_expectancy_fraction:.0%} of the {ref:+.2f}R the backtest "
             f"reads at the same ages (median {gate.get('median_age_days')}d)"
             if exp is not None and req is not None
             else "no qualifying signals yet")),
        "beats_benchmark": _cond(
            None if (sysret is None or bm.get("ret_pct") is None)
            else sysret > bm["ret_pct"],
            (f"system {sysret:+.1f}% vs {GATE.benchmark_label} "
             f"{bm['ret_pct']:+.1f}% over the same window"
             if sysret is not None and bm.get("ret_pct") is not None
             else "not measurable yet")),
        "hit_stop": _cond(
            None if gate.get("hit_stop_pct") is None
            else gate["hit_stop_pct"] <= GATE.max_hit_stop_pct,
            f"{gate.get('hit_stop_pct')}% stopped vs {GATE.max_hit_stop_pct}% ceiling"
            if gate.get("hit_stop_pct") is not None else "no closed signals yet"),
        "concentration": _cond(
            None if gate.get("best_trade_share_pct") is None
            else gate["best_trade_share_pct"] <= GATE.max_share_from_best_trade_pct,
            f"best trade is {gate.get('best_trade_share_pct')}% of positive R "
            f"vs {GATE.max_share_from_best_trade_pct}% ceiling"
            if gate.get("best_trade_share_pct") is not None else "no winners yet"),
    }

    decided = have_n and all(c["ok"] is not None for c in conditions.values())
    if not decided:
        verdict = "ACCRUING"
    elif all(c["ok"] for c in conditions.values()):
        verdict = "PASSED"
    else:
        verdict = "FAILED"

    days_left = (datetime.strptime(GATE.deadline, "%Y-%m-%d") - datetime.now()).days
    return {
        "generated": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "registered": "2026-07-26",
        "verdict": verdict,
        "progress_pct": round(min(100.0, gate.get("n_qualifying", 0)
                                  / max(GATE.min_signals, 1) * 100), 1),
        "deadline": GATE.deadline,
        "days_to_deadline": days_left,
        "ruler": GATE.ruler,
        "required": {
            "min_signals": GATE.min_signals,
            "min_age_days": GATE.min_age_days,
            # age-matched since the 2026-07-27 amendment: the bar moves with the
            # cohort's age because the ruler does. min_expectancy_r is retained
            # as the superseded flat bar so the amendment stays auditable.
            "min_expectancy_fraction": GATE.min_expectancy_fraction,
            "expectancy_r": req,
            "age_matched_reference_r": ref,
            "superseded_flat_min_expectancy_r": GATE.min_expectancy_r,
            "expectancy_curve": [list(p) for p in GATE.expectancy_curve],
            "max_hit_stop_pct": GATE.max_hit_stop_pct,
            "max_share_from_best_trade_pct": GATE.max_share_from_best_trade_pct,
            "pass_capital_pct": GATE.pass_capital_pct,
        },
        "cohort": gate,
        "cohort_running": gate_running,
        "legacy": legacy,
        "extended": extended,
        "conditions": conditions,
        "benchmark": {**bm, "label": GATE.benchmark_label, "note": GATE.benchmark_note},
        "benchmark2": {**bm2, "label": GATE.secondary_benchmark_label},
        "benchmark_context": context,
        "cohort_definition": (
            f"{' + '.join(GATE.cohort_kinds)} alerts from {GATE.cohort_start_date} — "
            "the entries the backtest validated. Excludes VALIDATED (EXTENDED), "
            "which the live system skips, and unsized signals the risk engine refuses."),
    }


def main() -> None:
    g = evaluate()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(g, f, indent=1)
    c = g["cohort"]
    print(f"GATE {g['verdict']}  ({c['n_qualifying']}/{GATE.min_signals} qualifying, "
          f"{g['days_to_deadline']}d to {g['deadline']})")
    for k, v in g["conditions"].items():
        mark = "?" if v["ok"] is None else ("PASS" if v["ok"] else "FAIL")
        print(f"  [{mark:>4}] {k}: {v['detail']}")
    b, b2 = g["benchmark"], g["benchmark2"]
    if b.get("ret_pct") is not None:
        print(f"  benchmark {b['sym']} {b['ret_pct']:+.2f}% "
              f"({b['from']} -> {b['to']}) · {b2['sym']} "
              f"{b2.get('ret_pct')}%")
    print(f"  legacy cohort (pre-fix scan): n={g['legacy']['n']}, "
          f"expectancy {g['legacy'].get('expectancy_r')}R (running read) "
          f"— reported, not judged")
    print(f"-> {OUT}")


if __name__ == "__main__":
    main()
