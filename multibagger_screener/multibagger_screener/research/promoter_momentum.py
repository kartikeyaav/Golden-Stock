"""
research/promoter_momentum.py — promoter buying + momentum (H25) as a
PORTFOLIO, to fix the forward test's rules on evidence rather than taste
(PREREG_2026-09-28_promoter_momentum.md §2, registered before this ran).

The same fixed grid and choice rule as research/value_breakout.py:
  positions 5 / 10  x  exits 30-week average / 3xATR chandelier  x  breadth exit off / on
chosen on 2016-2020 (MAR, among cells beating the equal-weight universe), read on
2021-2026, all cells reported. Then the registered comparison: the chosen cell
with MOMENTUM ALONE (H25 without the promoter purchase), same years, and the
RS-leader sleeve's configuration for reference.

    python -m research.promoter_momentum
"""

from __future__ import annotations

import itertools
import json
import os
import time

import numpy as np
import pandas as pd

from research.grid import load_grid, xrank
from research.hypotheses import h4_trend_template, h9_rs_leader
from research.insider_study import h25_grid, load_trades
from research.regime_test import regimes
from research.sim import SimConfig, perf, run
from research.strategy_grid import eqw_benchmark

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
PERIODS = {"2016-2020": ("2016-01-01", "2020-12-31"), "2021-2026": ("2021-01-01", None),
           "2016-2026": ("2016-01-01", None)}


def slots_used(g, res: dict, cfg: SimConfig, start: str) -> float | None:
    """The average share of the book's slots holding a position, in %."""
    eq, tr = res["equity"], res["trades"]
    if not len(eq):
        return None
    t0 = int(np.searchsorted(g.dates.values, np.datetime64(start)))
    last = t0 + len(eq) - 1
    if not len(tr):
        return 0.0
    ends = tr["exit_t"].fillna(last).astype(int).clip(upper=last)
    held = (ends - tr["entry_t"].astype(int)).clip(lower=0).sum()
    return round(float(held) / (len(eq) * cfg.max_positions) * 100, 1)


def cell_result(g, sig, rs, cfg, rb, reg: bool) -> dict:
    out = {}
    for p, (s, e) in PERIODS.items():
        res = run(g, sig, rs, cfg, pd.Timestamp(s), pd.Timestamp(e) if e else None,
                  risk_on=rb if reg else None)
        pf = perf(res["equity"])
        tr = res["trades"]
        out[p] = {**{k: v for k, v in pf.items() if k != "yearly"}, "yearly": pf.get("yearly"),
                  "trades": int(len(tr)),
                  "win_pct": round(float((tr["mult"] > 1).mean()) * 100, 1) if len(tr) else None,
                  "slots_used_pct": slots_used(g, res, cfg, s),
                  "best_mult": round(float(tr["mult"].max()), 2) if len(tr) else None}
    return out


def line(tag: str, cell: dict) -> str:
    a, b, c = cell["2016-2020"], cell["2021-2026"], cell["2016-2026"]
    return (f"{tag:44} | 2016-20 {a.get('cagr_pct')}% {a.get('max_dd_pct')}% | 2021-26 {b.get('cagr_pct')}% "
            f"{b.get('max_dd_pct')}% | 2016-26 {c.get('cagr_pct')}% {c.get('max_dd_pct')}% "
            f"trades {c.get('trades')} slots used {c.get('slots_used_pct')}%")


def main() -> int:
    t0 = time.time()
    g = load_grid()
    U = g.universe()
    tr = load_trades()
    mom = (h9_rs_leader(g) | h4_trend_template(g)) & U
    sig = h25_grid(g, tr) & U
    rs = xrank(g.ret(126), U)
    rb = regimes(g)["R-B breadth>=50%"]
    era = g.dates >= pd.Timestamp("2016-01-01")
    per_day = sig[era].sum(axis=1)
    print(f"H25 signal days: {int(sig.sum()):,}; names per session 2016-26: mean {per_day.mean():.1f}, "
          f"median {np.median(per_day):.0f}, sessions with none {float((per_day == 0).mean()) * 100:.0f}% "
          f"| momentum alone: mean {mom[era].sum(axis=1).mean():.0f} ({time.time() - t0:.0f}s)", flush=True)
    bench = {p: perf(eqw_benchmark(g, s, e)) for p, (s, e) in PERIODS.items()}
    print("equal-weight universe:", {p: (b.get("cagr_pct"), b.get("max_dd_pct")) for p, b in bench.items()},
          flush=True)
    rows = []
    for npos, (ex, par), reg in itertools.product((5, 10), (("sma", 150), ("chandelier", 3.0)), (False, True)):
        cfg = SimConfig(max_positions=npos, exit=ex, trail=int(par) if ex == "sma" else 50,
                        chandelier_k=float(par) if ex == "chandelier" else 3.0)
        cell = {"positions": npos, "exit": f"{ex}{par:g}", "breadth_exit": reg,
                **cell_result(g, sig, rs, cfg, rb, reg)}
        rows.append(cell)
        print(line(f"n={npos:2} {cell['exit']:12} breadth-exit={str(reg):5}", cell), flush=True)
    eq = bench["2016-2020"].get("cagr_pct") or 0
    ok = [r for r in rows if (r["2016-2020"].get("cagr_pct") or -99) > float(eq) and r["2016-2020"].get("mar")]
    passed = bool(ok)
    pool = ok or [r for r in rows if r["2016-2020"].get("mar")]
    chosen = max(pool, key=lambda r: r["2016-2020"]["mar"]) if pool else None
    comparison = {}
    if chosen:
        ex, reg = chosen["exit"], chosen["breadth_exit"]
        cfg = SimConfig(max_positions=chosen["positions"], exit="sma" if ex.startswith("sma") else "chandelier",
                        trail=150 if ex.startswith("sma") else 50,
                        chandelier_k=3.0)
        comparison["momentum alone, chosen cell"] = cell_result(g, mom, rs, cfg, rb, reg)
        print(line("momentum alone (same cell)", comparison["momentum alone, chosen cell"]), flush=True)
    mb_cfg = SimConfig(max_positions=5, exit="sma", trail=150)
    comparison["RS-leader sleeve config (5, sma150, breadth exit)"] = cell_result(
        g, h9_rs_leader(g) & U, rs, mb_cfg, rb, True)
    print(line("RS-leader sleeve (5, sma150, breadth exit)",
               comparison["RS-leader sleeve config (5, sma150, breadth exit)"]), flush=True)
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(os.path.join(OUT_DIR, "promoter_momentum.json"), "w", encoding="utf-8") as f:
        json.dump({"benchmark_eqw": bench, "selection_bar_passed": passed, "chosen_on_2016_2020": chosen,
                   "comparison": comparison, "cells": rows,
                   "signal": {"days": int(sig.sum()), "names_per_session_mean": round(float(per_day.mean()), 2),
                              "sessions_with_none_pct": round(float((per_day == 0).mean()) * 100, 1)}},
                  f, indent=1, default=str)
    if chosen:
        print(f"\nCHOSEN on 2016-2020 ({'passed' if passed else 'FAILED'} the selection bar): "
              f"n={chosen['positions']} {chosen['exit']} breadth-exit={chosen['breadth_exit']} "
              f"-> 2021-26 {chosen['2021-2026'].get('cagr_pct')}% / {chosen['2021-2026'].get('max_dd_pct')}%")
    print(f"done in {(time.time() - t0) / 60:.1f}m")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
