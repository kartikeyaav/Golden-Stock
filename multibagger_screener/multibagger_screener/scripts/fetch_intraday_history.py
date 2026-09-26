"""
scripts/fetch_intraday_history.py — 5-minute bars for the universe, the most
Yahoo will give (60 days), saved outside the repo.

Used to MEASURE the 3:10 PM breakout check before trusting it
(scripts/measure_intraday_proxy.py): does "above the pivot at 15:10 with the
volume on pace" agree with "closed above the pivot on the volume" often enough
to act on, and how far is a 15:20 fill from the official close?

    python scripts/fetch_intraday_history.py [--limit N]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

OUT = Path(os.environ.get("GS_HISTORY_DIR", str(Path.home() / "golden_stock_data" / "nse"))).parent / "intraday5m"


def yahoo_symbol(sym: str, manifest: dict) -> str:
    return manifest.get(sym, {}).get("yahoo_symbol") or f"{sym}.NS"


def main() -> int:
    import yfinance as yf
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    uni = pd.read_csv(os.path.join(ROOT, "universe.csv"))["symbol"].tolist()
    man_path = os.path.join(ROOT, "data_cache", "manifest.json")
    manifest = json.load(open(man_path, encoding="utf-8")) if os.path.exists(man_path) else {}
    todo = [s for s in uni if not (OUT / f"{s}.csv").exists()]
    if a.limit:
        todo = todo[: a.limit]
    print(f"{len(todo)} symbols to fetch -> {OUT}", flush=True)
    ok = fail = 0
    for i in range(0, len(todo), 40):
        chunk = todo[i:i + 40]
        tick = {yahoo_symbol(s, manifest): s for s in chunk}
        try:
            df = yf.download(list(tick), period="60d", interval="5m", group_by="ticker",
                             auto_adjust=False, threads=True, progress=False)
        except Exception as e:  # noqa: BLE001
            print("chunk failed:", type(e).__name__, str(e)[:100], flush=True)
            time.sleep(10)
            continue
        for yh, sym in tick.items():
            try:
                d = df[yh].dropna(how="all")
            except KeyError:
                fail += 1
                continue
            if d.empty:
                fail += 1
                continue
            d = d.reset_index().rename(columns=str.lower)
            tcol = "datetime" if "datetime" in d.columns else d.columns[0]
            d["ts"] = pd.to_datetime(d[tcol], utc=True).dt.tz_convert("Asia/Kolkata").dt.tz_localize(None)
            d[["ts", "open", "high", "low", "close", "volume"]].to_csv(OUT / f"{sym}.csv", index=False)
            ok += 1
        print(f"{min(i + 40, len(todo))}/{len(todo)}  ok {ok}  empty/failed {fail}", flush=True)
        time.sleep(1.5)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
