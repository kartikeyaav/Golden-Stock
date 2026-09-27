"""
research/value_breakout.py — cheap + new uptrend (H20) as a PORTFOLIO, to fix
the forward test's rules on evidence rather than taste.

The event study (research/fundamental_study.py) measured H20 events: a +18.6%
12-month median and the best 5x-in-2-years lift of anything tested — but only
2016-2026 has fundamentals, so no discovery/confirmation step was possible.
Here the same signal runs through research/sim.py with a small fixed grid:
  positions 5 / 10  x  exits 30-week average / 3xATR chandelier  x  breadth exit off / on
chosen on 2016-2020 (MAR, among cells beating the equal-weight universe), read on
2021-2026, and reported in full.

    python -m research.value_breakout
"""

from __future__ import annotations

import itertools
import json
import os
import time

import numpy as np
import pandas as pd

from research import fundamentals as F
from research.grid import load_grid, xrank
from research.hypotheses import h2_multi_year_base_breakout, h5_stage2_start
from research.regime_test import regimes
from research.sim import SimConfig, perf, run
from research.strategy_grid import eqw_benchmark

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
PERIODS = {"2016-2020": ("2016-01-01", "2020-12-31"), "2021-2026": ("2021-01-01", None),
           "2016-2026": ("2016-01-01", None)}


def main() -> int:
    t0 = time.time()
    g = load_grid()
    U = g.universe()
    fg = F.grids(g)
    sig = F.h20_cheap_new_uptrend(g, fg, h2_multi_year_base_breakout(g), h5_stage2_start(g)) & U
    rs = xrank(g.ret(126), U)
    rb = regimes(g)["R-B breadth>=50%"]
    print(f"H20 signal days: {int(sig.sum()):,} ({time.time() - t0:.0f}s)", flush=True)
    bench = {p: perf(eqw_benchmark(g, s, e)) for p, (s, e) in PERIODS.items()}
    print("equal-weight universe:", {p: (b.get("cagr_pct"), b.get("max_dd_pct")) for p, b in bench.items()})
    rows = []
    for npos, (ex, par), reg in itertools.product((5, 10), (("sma", 150), ("chandelier", 3.0)), (False, True)):
        cfg = SimConfig(max_positions=npos, exit=ex, trail=int(par) if ex == "sma" else 50,
                        chandelier_k=float(par) if ex == "chandelier" else 3.0)
        cell = {"positions": npos, "exit": f"{ex}{par:g}", "breadth_exit": reg}
        for p, (s, e) in PERIODS.items():
            res = run(g, sig, rs, cfg, pd.Timestamp(s), pd.Timestamp(e) if e else None,
                      risk_on=rb if reg else None)
            pf = perf(res["equity"])
            tr = res["trades"]
            cell[p] = {**{k: v for k, v in pf.items() if k != "yearly"}, "yearly": pf.get("yearly"),
                       "trades": int(len(tr)),
                       "win_pct": round(float((tr["mult"] > 1).mean()) * 100, 1) if len(tr) else None}
        rows.append(cell)
        a, b, c = cell["2016-2020"], cell["2021-2026"], cell["2016-2026"]
        print(f"n={npos:2} {cell['exit']:12} breadth-exit={str(reg):5} | 2016-20 {a.get('cagr_pct')}% {a.get('max_dd_pct')}% "
              f"| 2021-26 {b.get('cagr_pct')}% {b.get('max_dd_pct')}% | 2016-26 {c.get('cagr_pct')}% "
              f"{c.get('max_dd_pct')}% trades {c.get('trades')}", flush=True)
    eq = bench["2016-2020"].get("cagr_pct") or 0
    ok = [r for r in rows if (r["2016-2020"].get("cagr_pct") or -99) > float(eq) and r["2016-2020"].get("mar")]
    chosen = max(ok, key=lambda r: r["2016-2020"]["mar"]) if ok else None
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(os.path.join(OUT_DIR, "value_breakout.json"), "w", encoding="utf-8") as f:
        json.dump({"benchmark_eqw": bench, "chosen_on_2016_2020": chosen, "cells": rows}, f, indent=1, default=str)
    if chosen:
        print(f"\nCHOSEN on 2016-2020: n={chosen['positions']} {chosen['exit']} breadth-exit={chosen['breadth_exit']} "
              f"-> 2021-26 {chosen['2021-2026'].get('cagr_pct')}% / {chosen['2021-2026'].get('max_dd_pct')}%")
    print(f"done in {(time.time() - t0) / 60:.1f}m")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
