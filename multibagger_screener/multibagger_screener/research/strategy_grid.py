"""
research/strategy_grid.py — PREREG_2026-09-26 §5: the portfolio grid on the
survivorship-free panel, EVERY cell reported, selection on discovery only.

Signals: the hypotheses that survived confirmation with lift >= 1.5
(power play H7, RS leader H9, discovery H14 — research/out/event_study*.md),
alone and as one combined signal. Slots go to the strongest 6-month relative
strength when more names signal than slots are free.
Grid: positions 5 / 8 / 12 / 20 x exits 50-day average / 30-week average /
3xATR chandelier x fills next-open / signal-day close x breadth exposure on / off.
Periods: discovery 2006-01 -> 2015-12 and confirmation 2016-01 -> 2026-09, each
from fresh capital; the configuration chosen on discovery (best MAR with CAGR
> the equal-weight universe) is then read on confirmation.

    python -m research.strategy_grid [--signals H7,H9,H14,C] [--quick]
"""

from __future__ import annotations

import argparse
import itertools
import json
import os
import time

import numpy as np
import pandas as pd

from research.grid import load_grid, xrank, roll
from research.hypotheses import HYPOTHESES
from research.sim import SimConfig, run, perf

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
PERIODS = {"discovery": ("2006-01-02", "2015-12-31"), "confirmation": ("2016-01-01", None)}


def breadth_exposure(g) -> np.ndarray:
    """The live system's rule on this universe: 1.0 when >= 50% of universe
    members close above their 200-day average, else 0.5; unknown = 0.5."""
    U = g.universe()
    s200 = g.sma(200)
    ok = U & np.isfinite(s200)
    above = (g.c > s200) & ok
    frac = above.sum(axis=1) / np.maximum(ok.sum(axis=1), 1)
    exp = np.where(frac >= 0.5, 1.0, 0.5)
    exp[ok.sum(axis=1) < 100] = 0.5
    return exp


def eqw_benchmark(g, start, end) -> pd.Series:
    """Equal weight of universe members, reset monthly; a member that stops
    trading keeps its last price until the next reset (it does not vanish)."""
    U = g.universe()
    cf = pd.DataFrame(g.c, index=g.dates).ffill()
    d = g.dates
    sel = (d >= pd.Timestamp(start)) & ((d <= pd.Timestamp(end)) if end else True)
    idx = np.nonzero(sel)[0]
    months = d[idx].to_period("M")
    firsts = pd.Series(idx, index=months).groupby(level=0).first().to_numpy()
    val, out = 1.0, {}
    for k, t0 in enumerate(firsts):
        t1 = firsts[k + 1] if k + 1 < len(firsts) else idx[-1]
        mem = np.nonzero(U[t0 - 1])[0]
        base = cf.iloc[t0, mem].to_numpy()
        good = np.isfinite(base) & (base > 0)
        mem, base = mem[good], base[good]
        if not len(mem):
            continue
        seg = cf.iloc[t0:t1 + 1, mem].to_numpy() / base
        path = np.nanmean(seg, axis=1) * val
        for t, x in zip(range(t0, t1 + 1), path):
            out[d[t]] = x
        val = float(path[-1])
    return pd.Series(out).sort_index()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--signals", default="H7,H9,H14,C")
    ap.add_argument("--quick", action="store_true", help="10-position, next-open cells only")
    ap.add_argument("--tag", default="")
    a = ap.parse_args()
    t0 = time.time()
    g = load_grid()
    U = g.universe()
    rs = xrank(g.ret(126), U)                               # slot priority: 6-month RS
    sig = {}
    for key in ("H7", "H9", "H14"):
        fn = [f for n, f in HYPOTHESES.items() if n.split()[0] == key][0]
        sig[key] = fn(g) & U
    sig["C"] = sig["H7"] | sig["H9"] | sig["H14"]
    exposure = breadth_exposure(g)
    print(f"grid ready ({time.time() - t0:.0f}s); signal days: "
          + ", ".join(f"{k} {int(v.sum()):,}" for k, v in sig.items()), flush=True)

    bench = {p: perf(eqw_benchmark(g, s, e)) for p, (s, e) in PERIODS.items()}
    print("equal-weight universe:", {p: (b.get("cagr_pct"), b.get("max_dd_pct")) for p, b in bench.items()},
          flush=True)

    names = [s for s in a.signals.split(",") if s in sig]
    positions = (10,) if a.quick else (5, 8, 12, 20)
    exits = (("sma", 50), ("sma", 150), ("chandelier", 3.0))
    fills = ("open",) if a.quick else ("open", "close")
    regimes = (True, False)
    rows = []
    for sname, npos, (ex, par), fill, reg in itertools.product(names, positions, exits, fills, regimes):
        cfg = SimConfig(max_positions=npos, fill=fill, exit=ex,
                        trail=int(par) if ex == "sma" else 50,
                        chandelier_k=float(par) if ex == "chandelier" else 3.0)
        cell = {"signal": sname, "positions": npos, "exit": f"{ex}{par:g}", "fill": fill,
                "breadth": reg}
        for pname, (s, e) in PERIODS.items():
            res = run(g, sig[sname], rs, cfg, pd.Timestamp(s), pd.Timestamp(e) if e else None,
                      exposure=exposure if reg else None)
            pf = perf(res["equity"])
            tr = res["trades"]
            mult = tr["mult"] if len(tr) else pd.Series(dtype=float)
            cell[pname] = {**{k: v for k, v in pf.items() if k != "yearly"}, "yearly": pf.get("yearly"),
                           "trades": int(len(tr)),
                           "win_pct": round(float((mult > 1).mean()) * 100, 1) if len(tr) else None,
                           "share_3x": round(float((mult >= 3).mean()) * 100, 1) if len(tr) else None,
                           "best_mult": round(float(mult.max()), 1) if len(tr) else None}
        rows.append(cell)
        d, c = cell["discovery"], cell["confirmation"]
        print(f"{sname:3} n={npos:2} {cell['exit']:12} {fill:5} breadth={str(reg):5} | "
              f"disc CAGR {d.get('cagr_pct')}% DD {d.get('max_dd_pct')}% | "
              f"conf CAGR {c.get('cagr_pct')}% DD {c.get('max_dd_pct')}% "
              f"({time.time() - t0:.0f}s)", flush=True)

    # PREREG §5/§6: choose on discovery only (best MAR among cells beating the
    # equal-weight universe's discovery CAGR), then read that cell on confirmation
    eq_disc = bench["discovery"].get("cagr_pct", 0)
    ok = [r for r in rows if (r["discovery"].get("cagr_pct") or -99) > eq_disc and r["discovery"].get("mar")]
    chosen = max(ok, key=lambda r: r["discovery"]["mar"]) if ok else None
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(os.path.join(OUT_DIR, f"strategy_grid{a.tag}.json"), "w", encoding="utf-8") as f:
        json.dump({"benchmark_eqw": bench, "chosen_on_discovery": chosen, "cells": rows}, f, indent=1,
                  default=str)
    if chosen:
        print(f"\nCHOSEN on discovery: {chosen['signal']} n={chosen['positions']} {chosen['exit']} "
              f"{chosen['fill']} breadth={chosen['breadth']} -> confirmation CAGR "
              f"{chosen['confirmation'].get('cagr_pct')}% DD {chosen['confirmation'].get('max_dd_pct')}%")
    print(f"done in {(time.time() - t0) / 60:.1f}m")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
