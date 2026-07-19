"""
scripts/journal_outcomes.py — fill in what happened AFTER each journaled
signal (the forward-validation scorecard). Reads journal/signals_journal.csv,
computes per BUY/RE-ENTRY row from the price cache:

  days_elapsed, return_to_date_pct, max_favorable_R, hit_suggested_stop,
  r_multiple_if_stopped_or_open (marked-to-market on the suggested stop plan)

Writes journal/journal_outcomes.csv (regenerated each run — the journal
itself is never touched). Run weekly, or whenever curious:

    python scripts/journal_outcomes.py
"""

from __future__ import annotations

import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.cache import load_ohlcv

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JOURNAL = os.path.join(ROOT, "journal", "signals_journal.csv")
OUT = os.path.join(ROOT, "journal", "journal_outcomes.csv")


def main() -> None:
    if not os.path.exists(JOURNAL):
        print("no journal yet — outcomes will exist once the first alert is logged")
        return
    j = pd.read_csv(JOURNAL, parse_dates=["logged_at"])
    buys = j[j["kind"].isin(["BUY CANDIDATE", "RE-ENTRY WINDOW", "EPISODIC PIVOT"])].copy()
    if buys.empty:
        print("journal has no buy-type signals yet")
        return

    rows = []
    for _, r in buys.iterrows():
        sym = r["symbol"]
        df = load_ohlcv(sym)
        if df is None:
            continue
        after = df[df["date"] > r["logged_at"]]
        entry = float(r["close"])
        stop = float(r["stop_suggested"]) if pd.notna(r["stop_suggested"]) and r["stop_suggested"] != "" else None
        risk = (entry - stop) if stop else None

        if after.empty:
            rows.append({**r.to_dict(), "days_elapsed": 0, "status": "no data yet"})
            continue

        hit_stop = bool(stop and (after["low"] <= stop).any())
        stop_hit_date = after.loc[after["low"] <= stop, "date"].iloc[0] if hit_stop else None
        # favorable excursion measured only until the stop was hit (if it was)
        favorable_window = after[after["date"] <= stop_hit_date] if hit_stop else after
        max_fav_r = (float(favorable_window["high"].max()) - entry) / risk if risk else None
        last_close = float(after["close"].iloc[-1])

        rows.append({
            **r.to_dict(),
            "days_elapsed": int((after["date"].iloc[-1] - r["logged_at"]).days),
            "return_to_date_pct": round((last_close / entry - 1) * 100, 2),
            "max_favorable_R": round(max_fav_r, 2) if max_fav_r is not None else "",
            "hit_suggested_stop": hit_stop,
            "r_to_date": round((last_close - entry) / risk, 2) if risk and not hit_stop else (-1.0 if hit_stop else ""),
            "status": "stopped" if hit_stop else "open",
        })

    out = pd.DataFrame(rows)
    out.to_csv(OUT, index=False)
    closed = out[out["status"] == "stopped"]
    open_ = out[out["status"] == "open"]
    print(f"{len(out)} buy signals tracked -> {OUT}")
    print(f"  open: {len(open_)}  stopped: {len(closed)}")
    if len(out):
        r_vals = pd.to_numeric(out["r_to_date"], errors="coerce").dropna()
        if len(r_vals):
            print(f"  expectancy to date: {r_vals.mean():+.2f}R across {len(r_vals)} signals")


if __name__ == "__main__":
    main()
