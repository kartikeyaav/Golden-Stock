"""
scripts/validate_exemplars.py — sensitivity check across known winners:
would the stage tagger have flagged the 2023-2026 multibaggers as CONFIRMED
(buyable) during their runs, and how much of the move came AFTER that signal?

Walks month-end dates, re-runs tag_stock() as of each date (no look-ahead:
only data up to that date is passed in), then reports per stock: the first
CONFIRMED tag, price at that signal, the peak afterwards, and the tag mix
over time.

HONESTY NOTE (Design Law #4): this measures CAPTURE only — whether the logic
catches known winners. It says nothing about how many losers would ALSO have
been flagged; that's the full-universe baseline backtest's job. "Upside after
signal" is peak-based (nobody sells the top) — realizable gains come from the
two-lot backtest, not this table.

    python scripts/validate_exemplars.py MAZDOCK BEL SUZLON ... --start 2022-01-01
"""

from __future__ import annotations

import argparse
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.cache import load_ohlcv
from scoring.stage_tagger import tag_stock

MIN_ROWS = 260  # ~1 year of daily data before the first scan (tagger needs 45+ weeks)


def month_end_dates(df: pd.DataFrame, start: str) -> list[pd.Timestamp]:
    d = df["date"]
    key = d.dt.year * 100 + d.dt.month
    ends = df.loc[key != key.shift(-1), "date"]
    return [t for t in ends if t >= pd.Timestamp(start)]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("symbols", nargs="+")
    ap.add_argument("--bench", default="NIFTY50")
    ap.add_argument("--start", default="2022-01-01")
    args = ap.parse_args()

    bench = load_ohlcv(args.bench)

    rows = []
    for sym in args.symbols:
        df = load_ohlcv(sym)
        if df is None:
            print(f"[skip] {sym}: not cached")
            continue

        timeline: list[tuple[pd.Timestamp, str, float]] = []
        for t in month_end_dates(df, args.start):
            sub = df[df["date"] <= t]
            if len(sub) < MIN_ROWS:
                continue
            b = bench[bench["date"] <= t] if bench is not None else None
            try:
                tag = tag_stock(sub.reset_index(drop=True), b)["tag"]
            except Exception as e:  # noqa: BLE001
                tag = f"ERR({e})"
            timeline.append((t, tag, float(sub["close"].iloc[-1])))

        if not timeline:
            rows.append({"symbol": sym, "first_confirmed": "insufficient history"})
            continue

        tags = [x[1] for x in timeline]
        first_c = next((x for x in timeline if x[1] == "CONFIRMED"), None)

        row = {
            "symbol": sym,
            "scans": len(timeline),
            "conf_m": tags.count("CONFIRMED"),
            "ext_m": tags.count("EXTENDED"),
            "antic_m": tags.count("ANTICIPATION"),
            "broken_m": tags.count("BROKEN"),
            "latest_tag": tags[-1],
        }
        if first_c:
            t0, _, p0 = first_c
            after = df[df["date"] >= t0]
            peak = float(after["high"].max())
            latest_close = float(df["close"].iloc[-1])
            row.update({
                "first_confirmed": str(t0.date()),
                "px_at_signal": round(p0, 1),
                "peak_after": round(peak, 1),
                "upside_pct": round((peak / p0 - 1) * 100, 1),
                "now_vs_signal_pct": round((latest_close / p0 - 1) * 100, 1),
            })
        else:
            row["first_confirmed"] = "NEVER"
        rows.append(row)

    out = pd.DataFrame(rows)
    col_order = ["symbol", "first_confirmed", "px_at_signal", "peak_after", "upside_pct",
                 "now_vs_signal_pct", "conf_m", "ext_m", "antic_m", "broken_m",
                 "latest_tag", "scans"]
    out = out.reindex(columns=[c for c in col_order if c in out.columns])
    print(out.to_string(index=False))

    scanned = out[out.get("scans").notna()] if "scans" in out.columns else out
    captured = (out["first_confirmed"].notna()
                & ~out["first_confirmed"].isin(["NEVER", "insufficient history"])).sum()
    print(f"\nCAPTURE: {captured}/{len(scanned)} scanned winners received a CONFIRMED "
          f"(buyable) tag at least once in the window.")
    print("Reminder: capture-only test. False-positive rate comes from the "
          "full-universe baseline backtest, not this table.")


if __name__ == "__main__":
    main()
