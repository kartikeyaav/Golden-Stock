"""
research/validate_panel.py — is the survivorship-free panel's split/bonus
adjustment right? Two independent checks.

1. The restatement factors themselves (NSE's prior close / our last close):
   after the weekend-session fix, ordinary sessions should show 1.0, and what
   remains should look like corporate actions (mostly < 1).
2. Against the Yahoo cache the live system uses (split-adjusted closes): for
   every symbol both sources cover, the ratio adjusted_NSE / Yahoo should be
   FLAT through time. A step in the ratio = one side mishandled an action.

    python -m research.validate_panel
"""

from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from data.nse_history import load_panel  # noqa: E402
from data.cache import load_ohlcv, list_cached  # noqa: E402

OUT = os.path.join(ROOT, "research", "out")


def main() -> int:
    p = load_panel()
    last = pd.DataFrame(p.close).ffill().shift(1).to_numpy()
    with np.errstate(divide="ignore", invalid="ignore"):
        f = p.prev_close / last
    live = np.isfinite(f) & ~np.isnan(p.close)
    ev = live & (np.abs(f - 1) > 0.002)
    bins = [0, 0.2, 0.5, 0.9, 0.98, 0.998, 1.002, 1.02, 1.1, 2, 50, np.inf]
    h = np.histogram(f[ev], bins=bins)[0]
    bands = {f"{a}-{b}": int(n) for a, b, n in zip(bins[:-1], bins[1:], h)}
    print("restatement factors by band:", bands)

    cached = set(list_cached())
    C = p.close * p.adj
    rows = []
    for sym in p.symbols:
        if sym not in cached:
            continue
        y = load_ohlcv(sym)
        if y is None or len(y) < 250:
            continue
        ys = y.set_index("date")["close"]
        ns = pd.Series(C[:, p.col[sym]], index=p.dates).dropna()
        both = ns.index.intersection(ys.index)
        if len(both) < 250:
            continue
        r = np.log(ns[both] / ys[both])
        r = r[np.isfinite(r)]
        if len(r) < 250:
            continue
        # a step: the largest jump in the (smoothed) ratio
        sm = r.rolling(5, center=True, min_periods=3).median()
        step = float(sm.diff().abs().max())
        rows.append({"sym": sym, "n": len(r), "ratio_sd": float(r.std()), "max_step": step,
                     "first": str(both[0].date()), "last": str(both[-1].date())})
    df = pd.DataFrame(rows).sort_values("max_step", ascending=False)
    flat = (df["max_step"] < 0.05).mean()
    print(f"symbols compared: {len(df)}; ratio flat (no step > 5%): {flat:.1%}; "
          f"median ratio sd {df['ratio_sd'].median():.4f}")
    print("largest steps:")
    print(df.head(12).to_string(index=False))
    os.makedirs(OUT, exist_ok=True)
    df.to_csv(os.path.join(OUT, "panel_vs_yahoo.csv"), index=False)
    with open(os.path.join(OUT, "panel_validation.json"), "w", encoding="utf-8") as fh:
        json.dump({"restatement_bands": bands, "compared": int(len(df)),
                   "flat_share": round(float(flat), 4),
                   "median_ratio_sd": round(float(df["ratio_sd"].median()), 5)}, fh, indent=1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
