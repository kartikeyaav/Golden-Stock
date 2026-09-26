"""
research/regime_test.py — the PREREG_2026-09-26 amendment: does a REGIME EXIT
(everything to cash while the market's own trend is broken) keep the bull-year
gains and cut the bear-year losses?

  R-A  the survivorship-free equal-weight universe index closes below its
       200-day average  -> risk off
  R-B  fewer than 50% of universe members close above their own 200-day
       average          -> risk off

Same signals, slots, exits, fills and costs as research/strategy_grid.py.
Chosen on discovery by MAR (among cells beating the equal-weight universe),
then read once on confirmation.

    python -m research.regime_test
"""

from __future__ import annotations

import itertools
import json
import os
import time

import numpy as np
import pandas as pd

from research.grid import load_grid, xrank, roll
from research.hypotheses import HYPOTHESES
from research.sim import SimConfig, run, perf
from research.strategy_grid import PERIODS, eqw_benchmark

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")


def regimes(g) -> dict[str, np.ndarray]:
    idx = eqw_benchmark(g, str(g.dates[0].date()), None).reindex(g.dates).ffill()
    sma = idx.rolling(200, min_periods=200).mean()
    ra = (idx > sma).to_numpy()                       # NaN compare -> False: unknown = off
    U = g.universe()
    s200 = g.sma(200)
    ok = U & np.isfinite(s200)
    frac = ((g.c > s200) & ok).sum(axis=1) / np.maximum(ok.sum(axis=1), 1)
    rb = (frac >= 0.5) & (ok.sum(axis=1) >= 100)
    return {"R-A index>200d": ra, "R-B breadth>=50%": rb}


def main() -> int:
    t0 = time.time()
    g = load_grid()
    U = g.universe()
    rs = xrank(g.ret(126), U)
    sig = {}
    for key in ("H7", "H9", "H14"):
        fn = [f for n, f in HYPOTHESES.items() if n.split()[0] == key][0]
        sig[key] = fn(g) & U
    sig["C"] = sig["H7"] | sig["H9"] | sig["H14"]
    reg = regimes(g)
    for k, r in reg.items():
        print(f"{k}: risk-on share of sessions {r.mean():.0%}", flush=True)
    bench = {p: perf(eqw_benchmark(g, s, e)) for p, (s, e) in PERIODS.items()}
    rows = []
    for sname, npos, (ex, par), fill, rname in itertools.product(
            ("C", "H7", "H9"), (5, 8, 12, 20), (("sma", 50), ("sma", 150), ("chandelier", 3.0)),
            ("open", "close"), tuple(reg)):
        cfg = SimConfig(max_positions=npos, fill=fill, exit=ex,
                        trail=int(par) if ex == "sma" else 50,
                        chandelier_k=float(par) if ex == "chandelier" else 3.0)
        cell = {"signal": sname, "positions": npos, "exit": f"{ex}{par:g}", "fill": fill, "regime": rname}
        for pname, (s, e) in PERIODS.items():
            res = run(g, sig[sname], rs, cfg, pd.Timestamp(s), pd.Timestamp(e) if e else None,
                      risk_on=reg[rname])
            pf = perf(res["equity"])
            tr = res["trades"]
            mult = tr["mult"] if len(tr) else pd.Series(dtype=float)
            cell[pname] = {**{k: v for k, v in pf.items() if k != "yearly"}, "yearly": pf.get("yearly"),
                           "trades": int(len(tr)),
                           "win_pct": round(float((mult > 1).mean()) * 100, 1) if len(tr) else None,
                           "share_3x": round(float((mult >= 3).mean()) * 100, 1) if len(tr) else None}
        rows.append(cell)
        d, c = cell["discovery"], cell["confirmation"]
        print(f"{sname:3} n={npos:2} {cell['exit']:12} {fill:5} {rname:17} | disc {d.get('cagr_pct')}% "
              f"DD {d.get('max_dd_pct')}% | conf {c.get('cagr_pct')}% DD {c.get('max_dd_pct')}% "
              f"({time.time() - t0:.0f}s)", flush=True)
    eq_disc = bench["discovery"].get("cagr_pct", 0)
    ok = [r for r in rows if (r["discovery"].get("cagr_pct") or -99) > eq_disc and r["discovery"].get("mar")]
    chosen = max(ok, key=lambda r: r["discovery"]["mar"]) if ok else None
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(os.path.join(OUT_DIR, "regime_test.json"), "w", encoding="utf-8") as f:
        json.dump({"benchmark_eqw": bench, "chosen_on_discovery": chosen, "cells": rows}, f, indent=1,
                  default=str)
    if chosen:
        print(f"\nCHOSEN on discovery: {chosen['signal']} n={chosen['positions']} {chosen['exit']} "
              f"{chosen['fill']} {chosen['regime']} -> disc {chosen['discovery'].get('cagr_pct')}% / "
              f"{chosen['discovery'].get('max_dd_pct')}% ; confirmation {chosen['confirmation'].get('cagr_pct')}% "
              f"/ {chosen['confirmation'].get('max_dd_pct')}%")
    print(f"done in {(time.time() - t0) / 60:.1f}m")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
