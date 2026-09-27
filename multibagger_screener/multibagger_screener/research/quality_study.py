"""
research/quality_study.py — does FUNDAMENTAL QUALITY make the momentum signals
better at finding multibaggers? (PREREG_2026-09-26 amendment 2026-09-27, asked
by the user: "the fundamentals of a company play a vital role".)

  H30  power play or RS leader AND quality (profit > 0, operating cash flow > 0,
       sales growth > 0, profit growth > 0 on the latest known year)
  H31  the same signals WITHOUT quality — the comparison
  H32  earnings acceleration (latest-year profit growth >= 25% and faster
       than the year before)
  H33  H32 AND power play or RS leader (CAN SLIM-style)

Scored exactly like the event study; fundamentals exist from 2016 only, so the
halves are 2016-2020 and 2021-2026.

    python -m research.quality_study
"""

from __future__ import annotations

import json
import os
import time

import numpy as np
import pandas as pd

from research import fundamentals as F
from research.event_study import HORIZONS, LABELS, dedupe, mechanical_exit, summarise
from research.grid import fwd_max, load_grid, roll
from research.hypotheses import h7_power_play, h9_rs_leader

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPLIT = pd.Timestamp("2020-12-31")
START = pd.Timestamp("2016-01-01")


def main() -> int:
    t0 = time.time()
    g = load_grid()
    U = g.universe()
    tab = pd.read_csv(os.path.join(ROOT, "value_fundamentals.csv"))
    fy = F.fy_grids(g, tab)
    have = np.isfinite(fy["np"]) & np.isfinite(fy["np_1"]) & np.isfinite(fy["cfo"])
    Q = F.quality(fy)
    A = F.earnings_acceleration(fy)
    mom = h7_power_play(g) | h9_rs_leader(g)
    era = (g.dates >= START)[:, None]
    rng = np.random.default_rng(7)
    tests = {
        "H0 every universe stock (2016 on, with fundamentals)": U & era & have & (rng.random(U.shape) < 1 / 60),
        "H0q quality companies only (random sample)": U & era & Q & (rng.random(U.shape) < 1 / 30),
        "H30 power play or RS leader + quality": mom & Q & era,
        "H31 power play or RS leader, NOT quality": mom & have & ~Q & era,
        "H32 earnings acceleration": A & era,
        "H33 earnings acceleration + power play or RS leader": A & mom & era,
    }
    print(f"grids ready ({time.time() - t0:.0f}s); quality share of universe cells with data since 2016: "
          f"{(Q & U & era).sum() / max((have & U & era).sum(), 1):.0%}", flush=True)
    lab = {k: g.mb(m, w) for k, (m, w) in LABELS.items()}
    base = {k: np.nanmean(np.where(U, v, np.nan), axis=1) for k, v in lab.items()}
    fr = {h: g.fwd_ret(h) for h in HORIZONS}
    fr_base = {h: np.nanmean(np.where(U, v, np.nan), axis=1) for h, v in fr.items()}
    lo250 = roll(g.c, 250, "min", minp=60)
    pk = fwd_max(g.c, 252)
    res = {}
    for name, sig in tests.items():
        t, j = dedupe(sig & U)
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
        a, b = ev[ev["date"] <= SPLIT], ev[ev["date"] > SPLIT]
        res[name] = {"all": summarise(ev), "2016-2020": summarise(a), "2021-2026": summarise(b)}
        m1, m2 = res[name]["2016-2020"].get("MB3_1y", {}), res[name]["2021-2026"].get("MB3_1y", {})
        r1 = (res[name]["all"].get("r252") or {})
        print(f"{name:55} n={len(ev):5}  tripled-in-1y lift 2016-20 {m1.get('lift')} / 2021-26 {m2.get('lift')} "
              f"| 12m median {r1.get('median')}% doubled {r1.get('share_2x')}%", flush=True)
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(os.path.join(OUT_DIR, "quality_study.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1, default=str)
    print(f"done in {(time.time() - t0) / 60:.1f}m")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
