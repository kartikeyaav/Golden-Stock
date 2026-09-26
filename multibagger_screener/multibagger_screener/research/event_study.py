"""
research/event_study.py — score every hypothesis exactly as PREREG_2026-09-26
§4 registers it, on the survivorship-free panel.

    python -m research.event_study [--only H1,H8] [--min-turnover 1.0]

Writes research/out/event_study.json and research/out/event_study.md.
"""

from __future__ import annotations

import argparse
import json
import os
import time

import numpy as np
import pandas as pd

from research.grid import Grid, load_grid, roll
from research.hypotheses import HYPOTHESES

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
DEDUPE = 120                      # first firing per stock per 120 sessions
DISCOVERY_END = pd.Timestamp("2015-12-31")
LABELS = {"MB2_1y": (2.0, 252), "MB3_1y": (3.0, 252), "MB5_2y": (5.0, 504),
          "MB10_3y": (10.0, 756)}
HORIZONS = (63, 126, 252)
STOP = 0.80                       # mechanical exit: -20% stop
TRAIL_AFTER = 20                  # ... and a close below the 50-day average after 20 sessions


def dedupe(sig: np.ndarray, gap: int = DEDUPE) -> tuple[np.ndarray, np.ndarray]:
    T, N = sig.shape
    last = np.full(N, -10**9)
    rows, cols = [], []
    for t in range(T):
        fire = sig[t] & (t - last >= gap)
        if fire.any():
            j = np.nonzero(fire)[0]
            rows.append(np.full(len(j), t, dtype=np.int32))
            cols.append(j.astype(np.int32))
            last[j] = t
    if not rows:
        return np.array([], dtype=np.int32), np.array([], dtype=np.int32)
    return np.concatenate(rows), np.concatenate(cols)


def mechanical_exit(g: Grid, t: np.ndarray, j: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Enter at t+1 open; exit at the next open after a close <= 80% of entry,
    or after a close below the 50-day average once 20 sessions have passed.
    Still open at the end of the data -> marked at the last close."""
    s50 = g.sma(50)
    mult = np.full(len(t), np.nan, dtype="float32")
    held = np.full(len(t), np.nan, dtype="float32")
    T = g.T
    for k in range(len(t)):
        tt, jj = t[k], j[k]
        if tt + 1 >= T:
            continue
        e = g.o[tt + 1, jj]
        if not np.isfinite(e) or e <= 0:
            continue
        c = g.c[tt + 1:, jj]
        sm = s50[tt + 1:, jj]
        n = len(c)
        idx = np.arange(n)
        stop_hit = c <= STOP * e
        trail_hit = (idx >= TRAIL_AFTER) & (c < sm)
        hit = np.nonzero((stop_hit | trail_hit) & np.isfinite(c))[0]
        if len(hit):
            s = hit[0]
            # exit at the next session's open; a stock that never trades again
            # exits at its last close
            nxt = g.o[tt + 2 + s:, jj]
            fin = np.nonzero(np.isfinite(nxt))[0]
            px = nxt[fin[0]] if len(fin) else c[s]
            mult[k] = px / e
            held[k] = s + 1
        else:
            fin = np.nonzero(np.isfinite(c))[0]
            if len(fin):
                mult[k] = c[fin[-1]] / e
                held[k] = fin[-1] + 1
    return mult, held


def summarise(ev: pd.DataFrame) -> dict:
    out = {"n": int(len(ev))}
    if not len(ev):
        return out
    for lab in LABELS:
        m = ev[lab].notna()
        if m.sum() >= 1:
            rate = ev.loc[m, lab].mean()
            base = ev.loc[m, f"base_{lab}"].mean()
            out[lab] = {"rate": round(float(rate) * 100, 2), "base": round(float(base) * 100, 2),
                        "lift": round(float(rate / base), 2) if base > 0 else None,
                        "n": int(m.sum())}
    for h in HORIZONS:
        m = ev[f"r{h}"].notna()
        if m.sum():
            out[f"r{h}"] = {"median": round(float(ev.loc[m, f"r{h}"].median()) * 100, 1),
                            "mean": round(float(ev.loc[m, f"r{h}"].mean()) * 100, 1),
                            "excess_median": round(float(ev.loc[m, f"x{h}"].median()) * 100, 1),
                            "excess_mean": round(float(ev.loc[m, f"x{h}"].mean()) * 100, 1),
                            "share_2x": round(float((ev.loc[m, f"r{h}"] >= 1.0).mean()) * 100, 1)}
    m = ev["mult"].notna()
    if m.sum():
        mm = ev.loc[m, "mult"]
        out["exit"] = {"median": round(float(mm.median()), 3), "mean": round(float(mm.mean()), 3),
                       "geo_mean": round(float(np.exp(np.log(mm.clip(lower=1e-3)).mean())), 3),
                       "share_2x": round(float((mm >= 2).mean()) * 100, 1),
                       "share_3x": round(float((mm >= 3).mean()) * 100, 1),
                       "share_5x": round(float((mm >= 5).mean()) * 100, 1),
                       "held_median": float(ev.loc[m, "held"].median())}
    e = ev.loc[ev["MB3_1y"] == 1, "early"].dropna()
    if len(e):
        out["earliness_mb3"] = round(float(e.median()), 2)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="")
    ap.add_argument("--min-turnover", type=float, default=1.0)
    ap.add_argument("--tag", default="")
    a = ap.parse_args()
    os.makedirs(OUT_DIR, exist_ok=True)
    t0 = time.time()
    g = load_grid()
    U = g.universe(a.min_turnover)
    print(f"grid {g.T} x {g.N}, universe cells {int(U.sum()):,} ({time.time() - t0:.0f}s)", flush=True)

    # labels, and each date's universe base rate / mean return (date-matched)
    lab = {k: g.mb(m, w) for k, (m, w) in LABELS.items()}
    base = {k: np.nanmean(np.where(U, v, np.nan), axis=1) for k, v in lab.items()}
    fr = {h: g.fwd_ret(h) for h in HORIZONS}
    fr_base = {h: np.nanmean(np.where(U, v, np.nan), axis=1) for h, v in fr.items()}
    lo250 = roll(g.c, 250, "min", minp=60)
    peak252 = g.get("pk252", lambda: __import__("research.grid", fromlist=["fwd_max"]).fwd_max(g.c, 252))
    print(f"labels ready ({time.time() - t0:.0f}s)", flush=True)

    todo = {k: f for k, f in HYPOTHESES.items()
            if not a.only or k.split()[0] in a.only.split(",")}
    todo = {"H0 every universe stock": None, **todo}
    results = {}
    for name, fn in todo.items():
        t1 = time.time()
        if fn is None:
            # calibration: a random 1-in-60 sample of universe cells
            rng = np.random.default_rng(7)
            sig = U & (rng.random(U.shape) < 1 / 60)
        else:
            sig = fn(g) & U
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
        pk = peak252[t, j]
        with np.errstate(divide="ignore", invalid="ignore"):
            ev["early"] = np.log(pk / e) / np.log(pk / lo250[t, j])
        ev["mult"], ev["held"] = mechanical_exit(g, t, j)
        disc = ev[ev["date"] <= DISCOVERY_END]
        conf = ev[ev["date"] > DISCOVERY_END]
        yearly = {}
        for y, grp in ev.groupby(ev["date"].dt.year):
            m = grp["MB3_1y"].notna()
            if m.sum() >= 20:
                b = grp.loc[m, "base_MB3_1y"].mean()
                yearly[int(y)] = {"n": int(m.sum()),
                                  "rate": round(float(grp.loc[m, "MB3_1y"].mean()) * 100, 2),
                                  "lift": round(float(grp.loc[m, "MB3_1y"].mean() / b), 2) if b > 0 else None,
                                  "x252_median": round(float(grp["x252"].median()) * 100, 1)
                                  if grp["x252"].notna().any() else None}
        results[name] = {"all": summarise(ev), "discovery": summarise(disc),
                         "confirmation": summarise(conf), "yearly": yearly}
        ev.assign(symbol=[g.symbols[x] for x in ev["j"]]).drop(columns=["t", "j"]).to_csv(
            os.path.join(OUT_DIR, f"events_{name.split()[0]}{a.tag}.csv.gz"), index=False)
        d = results[name]["discovery"].get("MB3_1y", {})
        c = results[name]["confirmation"].get("MB3_1y", {})
        print(f"{name:40} n={len(ev):6}  MB3_1y lift disc {d.get('lift')} conf {c.get('lift')}  "
              f"({time.time() - t1:.0f}s)", flush=True)
    with open(os.path.join(OUT_DIR, f"event_study{a.tag}.json"), "w", encoding="utf-8") as f:
        json.dump({"min_turnover_cr": a.min_turnover, "dedupe": DEDUPE,
                   "discovery_end": str(DISCOVERY_END.date()), "results": results}, f, indent=1)
    print(f"done in {time.time() - t0:.0f}s", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
