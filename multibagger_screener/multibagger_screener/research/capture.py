"""
research/capture.py — RECALL: of the stocks that actually tripled, how many
did each signal catch EARLY?

The event study (research/event_study.py) answers "when this signal fires, how
often does a multibagger follow?" (precision / lift). This answers the user's
other question — "are we identifying the money-printing stocks at all?":

  * an EPISODE is a stock tripling within 252 sessions from a local low: the
    lowest close of a run of days from which a 3x followed, through the peak;
  * EARLY means before the move was half done in log terms: the first close
    above low x sqrt(peak/low);
  * a signal CATCHES an episode if it fired, while the stock was in the
    point-in-time universe, between 20 sessions before the low and the
    halfway point;
  * the share of episodes that were even TRADABLE at the low (in the
    universe) is reported, because many multibaggers start too small to buy.

    python -m research.capture [--mult 3.0 --window 252]
"""

from __future__ import annotations

import argparse
import json
import os
import time

import numpy as np
import pandas as pd

from research.grid import load_grid, fwd_max
from research.hypotheses import HYPOTHESES

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")


def episodes(g, mult: float = 3.0, window: int = 252) -> pd.DataFrame:
    fm = fwd_max(g.c, window)
    qual = (fm >= mult * g.c) & np.isfinite(g.c)
    rows = []
    T = g.T
    for j in range(g.N):
        q = np.nonzero(qual[:, j])[0]
        if not len(q):
            continue
        k = 0
        while k < len(q):
            # a run of consecutive qualifying sessions (gaps of <= 5 allowed)
            s = k
            while k + 1 < len(q) and q[k + 1] - q[k] <= 5:
                k += 1
            run = q[s:k + 1]
            cj = g.c[:, j]
            t_low = int(run[np.nanargmin(cj[run])])
            seg = cj[t_low:min(T, t_low + window + 1)]
            t_peak = t_low + int(np.nanargmax(seg))
            low, peak = float(cj[t_low]), float(cj[t_peak])
            mid_px = low * np.sqrt(peak / low)
            after = np.nonzero(cj[t_low:t_peak + 1] >= mid_px)[0]
            t_mid = t_low + int(after[0]) if len(after) else t_peak
            rows.append({"j": j, "sym": g.symbols[j], "t_low": t_low, "t_mid": t_mid,
                         "t_peak": t_peak, "low": low, "peak": peak, "mult": peak / low,
                         "date_low": g.dates[t_low]})
            # the next episode must start after this peak
            k += 1
            while k < len(q) and q[k] <= t_peak:
                k += 1
    return pd.DataFrame(rows)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mult", type=float, default=3.0)
    ap.add_argument("--window", type=int, default=252)
    a = ap.parse_args()
    t0 = time.time()
    g = load_grid()
    U = g.universe()
    ep = episodes(g, a.mult, a.window)
    ep = ep[ep["t_low"] < g.T - a.window]                     # a full window must exist
    ep["tradable_at_low"] = U[ep["t_low"], ep["j"]]
    ep["tradable_by_mid"] = [bool(U[r.t_low:r.t_mid + 1, r.j].any()) for r in ep.itertuples()]
    print(f"{len(ep):,} episodes of >= {a.mult}x within {a.window} sessions; tradable at the low "
          f"{ep['tradable_at_low'].mean():.0%}, by the halfway point {ep['tradable_by_mid'].mean():.0%} "
          f"({time.time() - t0:.0f}s)", flush=True)
    out = {"episodes": int(len(ep)), "tradable_at_low_pct": round(float(ep["tradable_at_low"].mean()) * 100, 1),
           "tradable_by_mid_pct": round(float(ep["tradable_by_mid"].mean()) * 100, 1),
           "median_multiple": round(float(ep["mult"].median()), 2), "signals": {}}
    tr = ep[ep["tradable_by_mid"]].copy()
    for name, fn in HYPOTHESES.items():
        sig = fn(g) & U
        caught, first_rem = [], []
        for r in tr.itertuples():
            lo = max(0, r.t_low - 20)
            hits = np.nonzero(sig[lo:r.t_mid + 1, r.j])[0]
            if len(hits):
                t_hit = lo + int(hits[0])
                caught.append(True)
                e = g.o[min(t_hit + 1, g.T - 1), r.j]
                first_rem.append(r.peak / e if np.isfinite(e) and e > 0 else np.nan)
            else:
                caught.append(False)
        tr[name] = caught
        rem = pd.Series(first_rem, dtype=float)
        out["signals"][name] = {"caught_early_pct": round(float(np.mean(caught)) * 100, 1),
                                "median_multiple_left_at_first_signal": round(float(rem.median()), 2)
                                if rem.notna().any() else None}
        print(f"{name:40} caught early {np.mean(caught):6.1%}  multiple left at first signal "
              f"{rem.median():.2f}x", flush=True)
    anyc = tr[[n for n in HYPOTHESES]].any(axis=1)
    out["any_signal_caught_early_pct"] = round(float(anyc.mean()) * 100, 1)
    by_year = tr.assign(y=tr["date_low"].dt.year).groupby("y").size().to_dict()
    out["tradable_episodes_by_year"] = {int(k): int(v) for k, v in by_year.items()}
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(os.path.join(OUT_DIR, f"capture_{a.mult:g}x.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)
    tr.drop(columns=["j"]).to_csv(os.path.join(OUT_DIR, f"capture_{a.mult:g}x_episodes.csv.gz"), index=False)
    print(f"any signal caught early: {anyc.mean():.1%} of {len(tr):,} tradable episodes "
          f"({time.time() - t0:.0f}s)", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
