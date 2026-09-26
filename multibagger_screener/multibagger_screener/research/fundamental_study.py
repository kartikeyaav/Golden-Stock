"""
research/fundamental_study.py — H18-H20 (value / quality / turnaround) with the
same scoring as the event study, plus the survivorship bill for using them.

Fundamentals exist only for companies listed today, so a fundamental signal can
only fire on survivors. To show how much that alone flatters a result, the
price-only calibration sample (H0) and a price signal (H9) are ALSO scored on
the with-fundamentals subset: the gap between "all" and "survivors-only" is the
bias every H18-H20 number carries.

    python -m research.fundamental_study
"""

from __future__ import annotations

import json
import os
import time

import numpy as np
import pandas as pd

from research import fundamentals as F
from research.event_study import (DISCOVERY_END, HORIZONS, LABELS, dedupe, mechanical_exit,
                                  summarise)
from research.grid import load_grid, roll
from research.hypotheses import h2_multi_year_base_breakout, h5_stage2_start, h9_rs_leader

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")


def score(g, sig, lab, base, fr, fr_base, lo250, pk):
    t, j = dedupe(sig)
    ev = pd.DataFrame({"t": t, "j": j})
    ev["date"] = g.dates[t]
    for k, v in lab.items():
        ev[k] = v[t, j]
        ev[f"base_{k}"] = base[k][t]
    for h in HORIZONS:
        ev[f"r{h}"] = fr[h][t, j]
        ev[f"x{h}"] = fr[h][t, j] - fr_base[h][t]
    e = g.entry()[t, j]
    with np.errstate(divide="ignore", invalid="ignore"):
        ev["early"] = np.log(pk[t, j] / e) / np.log(pk[t, j] / lo250[t, j])
    ev["mult"], ev["held"] = mechanical_exit(g, t, j)
    return {"all": summarise(ev), "discovery": summarise(ev[ev["date"] <= DISCOVERY_END]),
            "confirmation": summarise(ev[ev["date"] > DISCOVERY_END])}


def main() -> int:
    t0 = time.time()
    g = load_grid()
    U = g.universe()
    fg = F.grids(g)
    cov = F.coverage(g, fg, U)
    print("coverage:", cov, f"({time.time() - t0:.0f}s)", flush=True)
    lab = {k: g.mb(m, w) for k, (m, w) in LABELS.items()}
    base = {k: np.nanmean(np.where(U, v, np.nan), axis=1) for k, v in lab.items()}
    fr = {h: g.fwd_ret(h) for h in HORIZONS}
    fr_base = {h: np.nanmean(np.where(U, v, np.nan), axis=1) for h, v in fr.items()}
    lo250 = roll(g.c, 250, "min", minp=60)
    from research.grid import fwd_max
    pk = fwd_max(g.c, 252)
    have = np.isfinite(fg["bm"])
    rng = np.random.default_rng(7)
    h0 = U & (rng.random(U.shape) < 1 / 60)
    h9 = h9_rs_leader(g) & U
    tests = {
        "H0 every universe stock (all)": h0,
        "H0 every universe stock (with fundamentals only)": h0 & have,
        "H9 RS leader (all)": h9,
        "H9 RS leader (with fundamentals only)": h9 & have,
        "H18 cheap + cash-generative": F.h18_cheap_cash_generative(g, fg) & U,
        "H19 turnaround": F.h19_turnaround(g, fg) & U,
        "H20 cheap + new uptrend": F.h20_cheap_new_uptrend(g, fg, h2_multi_year_base_breakout(g),
                                                           h5_stage2_start(g)) & U,
    }
    res = {}
    for name, sig in tests.items():
        res[name] = score(g, sig, lab, base, fr, fr_base, lo250, pk)
        d = res[name]["discovery"].get("MB3_1y", {})
        c = res[name]["confirmation"].get("MB3_1y", {})
        print(f"{name:52} n={res[name]['all'].get('n')}  MB3_1y lift disc {d.get('lift')} conf "
              f"{c.get('lift')}", flush=True)
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(os.path.join(OUT_DIR, "fundamental_study.json"), "w", encoding="utf-8") as f:
        json.dump({"coverage": cov, "results": res}, f, indent=1, default=str)
    print(f"done in {(time.time() - t0) / 60:.1f}m")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
