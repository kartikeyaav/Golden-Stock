"""
scripts/build_focus_list.py — Pipeline Steps 1-3 (weekly job): liquidity
filter + batch RS percentile rank + stage-1-improving inclusion, then stage
tags on the survivors. Writes focus_list.csv and prints the names that are
CONFIRMED / ANTICIPATION right now.

    python scripts/build_focus_list.py
"""

from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import TECHNICAL, UNIVERSE
from data.cache import load_ohlcv, list_cached
from scoring.stage_tagger import classify_stage, rs_metrics, tag_stock

MIN_ROWS = 260          # need ~1 trading year for RS-12m and stage read
RS_PCTILE_FLOOR = 60.0  # brief section 2A step 3


def main() -> None:
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    universe = pd.read_csv(os.path.join(root, "universe.csv"))
    bench = load_ohlcv("NIFTY50")
    if bench is None:
        print("NIFTY50 benchmark missing from cache — run fetch_data.py first")
        sys.exit(1)

    cached = set(list_cached())
    rows = []
    for _, u in universe.iterrows():
        sym = u["symbol"]
        if sym not in cached:
            continue
        df = load_ohlcv(sym)
        if df is None or len(df) < MIN_ROWS:
            continue

        # liquidity: mean 20d turnover in Rs crore
        tail = df.tail(20)
        turnover_cr = float((tail["close"] * tail["volume"]).mean() / 1e7)
        if turnover_cr < UNIVERSE.min_avg_daily_turnover_cr:
            continue
        if float(df["close"].iloc[-1]) < UNIVERSE.min_price:
            continue

        rs = rs_metrics(df, bench)
        stage = classify_stage(df)
        rows.append({
            "symbol": sym, "industry": u.get("industry", ""),
            "index_source": u.get("index_source", ""),
            "turnover_cr": round(turnover_cr, 2),
            "rs_blend_raw": rs.get("rs_blend"),
            "rs_improving": rs.get("rs_improving"),
            "stage": stage.get("stage"),
            "last_close": float(df["close"].iloc[-1]),
        })

    scored = pd.DataFrame(rows).dropna(subset=["rs_blend_raw"])
    scored["rs_pctile"] = scored["rs_blend_raw"].rank(pct=True) * 100

    in_focus = (
        (scored["rs_pctile"] >= RS_PCTILE_FLOOR)
        | ((scored["stage"] == 1) & (scored["rs_improving"] == True))  # noqa: E712
    )
    focus = scored[in_focus].sort_values("rs_pctile", ascending=False).reset_index(drop=True)

    print(f"cached+liquid+history-ok: {len(scored)}  ->  focus list: {len(focus)}")

    # stage-tag the focus list (the daily-job read, run once here)
    tags = []
    for _, r in focus.iterrows():
        df = load_ohlcv(r["symbol"])
        t = tag_stock(df, bench)
        tags.append(t["tag"])
    focus["tag"] = tags

    out = os.path.join(root, "focus_list.csv")
    focus.to_csv(out, index=False)
    print(f"written -> {out}")
    print("\ntag counts:", focus["tag"].value_counts().to_dict())

    for tag in ("CONFIRMED", "ANTICIPATION"):
        sub = focus[focus["tag"] == tag]
        if not sub.empty:
            print(f"\n{tag} now ({len(sub)}):")
            cols = ["symbol", "industry", "rs_pctile", "turnover_cr", "last_close"]
            print(sub[cols].round(1).to_string(index=False))


if __name__ == "__main__":
    main()
