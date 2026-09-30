"""
research/mb_portfolio.py — the rebuilt multibagger score as a PORTFOLIO
(PREREG_2026-09-29_multibagger_factors.md, phase 2 rule registered before
the full results):

  entry   the score is in the top 10% of the universe that day (score > 0),
          ranked by score, then 6-month relative strength
  grid    5 / 10 positions x 30-week or 3xATR exit x breadth exit off / on
  choice  the best MAR on 2016-2020 among cells beating the equal-weight
          universe; read once on 2021-2026
  compare momentum alone and the promoter-buying signal (H25) on the chosen cell

    python -m research.mb_portfolio
"""

from __future__ import annotations

import itertools
import json
import os
import time

import numpy as np
import pandas as pd

from research import mb_score
from research.factor_study import (annual_table, dated_grids, factors, mcap_grid, q_grid, quarterly_table,
                                   shp_table)
from research.grid import load_grid, roll, xrank
from research.insider_study import grid_of, h25_grid, load_trades, promoter_purchases, signal_rows
from research.regime_test import regimes
from research.sim import SimConfig, perf, run
from research.strategy_grid import eqw_benchmark

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
PERIODS = {"2016-2020": ("2016-01-01", "2020-12-31"), "2021-2026": ("2021-01-01", None), "2016-2026": ("2016-01-01", None)}
Q1_NAME = "Q1 quarterly: profit +25%, sales +20% on the same quarter last year"


def flags_and_score(g):
    at, st = annual_table(), shp_table()
    fy = dated_grids(g, at, "fy", ("sales", "op", "np", "cfo", "cfi", "eq", "borrow", "assets", "roce"), "10-01", backs=(0, 1))
    sh = dated_grids(g, st, "yr", ("prom", "fii", "dii", "nsh"), "05-01", backs=(0, 1))
    mc = mcap_grid(g, at)
    tr = load_trades()
    promo60 = roll(grid_of(g, signal_rows(g, promoter_purchases(tr))).astype("float32"), 60, "max", minp=1) > 0
    flags = factors(g, fy, sh, mc, promo60)
    qt = quarterly_table()
    flags[Q1_NAME] = q_grid(g, qt) if len(qt) else np.zeros((g.T, g.N), bool)
    flags[mb_score.H25_KEY] = h25_grid(g, tr)
    cfg = mb_score.config()
    return flags, cfg, mb_score.score(flags, cfg)


def cell(g, sig, rank, cfg: SimConfig, rb, reg: bool) -> dict:
    out = {}
    for p, (s, e) in PERIODS.items():
        res = run(g, sig, rank, cfg, pd.Timestamp(s), pd.Timestamp(e) if e else None, risk_on=rb if reg else None)
        pf = perf(res["equity"])
        tr = res["trades"]
        out[p] = {**{k: v for k, v in pf.items() if k != "yearly"}, "yearly": pf.get("yearly"), "trades": int(len(tr)),
                  "win_pct": round(float((tr["mult"] > 1).mean()) * 100, 1) if len(tr) else None,
                  "best_mult": round(float(tr["mult"].max()), 2) if len(tr) else None}
    return out


def line(tag, c):
    a, b, d = c["2016-2020"], c["2021-2026"], c["2016-2026"]
    return (f"{tag:46} | 2016-20 {a.get('cagr_pct')}% {a.get('max_dd_pct')}% | 2021-26 {b.get('cagr_pct')}% "
            f"{b.get('max_dd_pct')}% | 2016-26 {d.get('cagr_pct')}% {d.get('max_dd_pct')}% trades {d.get('trades')}")


def main() -> int:
    t0 = time.time()
    g = load_grid()
    U = g.universe()
    flags, cfgw, sc = flags_and_score(g)
    print("survivors and weights:", json.dumps({k: v["weight"] for k, v in cfgw.items()}, indent=0), flush=True)
    rs = xrank(g.ret(126), U)
    # as registered: the top 10% of the UNIVERSE by score (a zero never enters),
    # not the top 10% of the names that scored at all
    sig = U & (sc > 0) & (xrank(sc, U) >= 0.90)
    rank = np.nan_to_num(sc) * 1000 + np.nan_to_num(rs)
    mom = flags["F momentum alone (RS leader or trend template)"] & U
    h25 = flags[mb_score.H25_KEY] & U
    rb = regimes(g)["R-B breadth>=50%"]
    era = g.dates >= pd.Timestamp("2016-01-01")
    print(f"signal: {int(sig[era].sum()):,} stock-days; {sig[era].sum(axis=1).mean():.1f} names a session ({time.time() - t0:.0f}s)", flush=True)
    bench = {p: perf(eqw_benchmark(g, s, e)) for p, (s, e) in PERIODS.items()}
    rows = []
    for npos, (ex, par), reg in itertools.product((5, 10), (("sma", 150), ("chandelier", 3.0)), (False, True)):
        cfg = SimConfig(max_positions=npos, exit=ex, trail=int(par) if ex == "sma" else 50, chandelier_k=float(par) if ex == "chandelier" else 3.0)
        c = {"positions": npos, "exit": f"{ex}{par:g}", "breadth_exit": reg, **cell(g, sig, rank, cfg, rb, reg)}
        rows.append(c)
        print(line(f"n={npos:2} {c['exit']:12} breadth-exit={str(reg):5}", c), flush=True)
    eq = bench["2016-2020"].get("cagr_pct") or 0
    ok = [r for r in rows if (r["2016-2020"].get("cagr_pct") or -99) > float(eq) and r["2016-2020"].get("mar")]
    pool = ok or [r for r in rows if r["2016-2020"].get("mar")]
    chosen = max(pool, key=lambda r: r["2016-2020"]["mar"]) if pool else None
    comparison = {}
    if chosen:
        cfg = SimConfig(max_positions=chosen["positions"], exit="sma" if chosen["exit"].startswith("sma") else "chandelier",
                        trail=150 if chosen["exit"].startswith("sma") else 50, chandelier_k=3.0)
        for tag, s2 in (("momentum alone", mom), ("promoter buying + momentum (H25)", h25)):
            comparison[tag] = cell(g, s2, rs, cfg, rb, chosen["breadth_exit"])
            print(line(tag + " (same cell)", comparison[tag]), flush=True)
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(os.path.join(OUT_DIR, "mb_portfolio.json"), "w", encoding="utf-8") as f:
        json.dump({"weights": cfgw, "benchmark_eqw": bench, "selection_bar_passed": bool(ok), "chosen_on_2016_2020": chosen,
                   "comparison": comparison, "cells": rows}, f, indent=1, default=str)
    if chosen:
        print(f"\nCHOSEN on 2016-2020 ({'passed' if ok else 'FAILED'} the selection bar): n={chosen['positions']} {chosen['exit']} "
              f"breadth-exit={chosen['breadth_exit']} -> 2021-26 {chosen['2021-2026'].get('cagr_pct')}% / {chosen['2021-2026'].get('max_dd_pct')}%")
    print(f"done in {(time.time() - t0) / 60:.1f}m")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
