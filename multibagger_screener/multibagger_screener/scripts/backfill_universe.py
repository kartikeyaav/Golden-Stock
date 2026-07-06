"""
scripts/backfill_universe.py — bulk backfill every universe.csv symbol into
the local cache from Yahoo (SYMBOL -> SYMBOL.NS). Skips symbols already
cached with data through the requested start. Failures are logged and
skipped — some NSE symbols simply don't exist on Yahoo under the same code.

    python scripts/backfill_universe.py --start 2019-01-01 --pause 0.4
"""

from __future__ import annotations

import argparse
import os
import sys
import time

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.cache import load_manifest
from data.yahoo_loader import fetch_yahoo_daily
from data.cache import save_ohlcv


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", default="2019-01-01")
    parser.add_argument("--pause", type=float, default=0.4)
    parser.add_argument("--universe", default=None)
    args = parser.parse_args()

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    universe_path = args.universe or os.path.join(root, "universe.csv")
    universe = pd.read_csv(universe_path)
    manifest = load_manifest()

    ok = skipped = failed = 0
    failures: list[str] = []
    t0 = time.time()

    for i, sym in enumerate(universe["symbol"], 1):
        if sym in manifest and manifest[sym].get("rows", 0) > 250:
            skipped += 1
            continue
        try:
            df = fetch_yahoo_daily(f"{sym}.NS", args.start)
            save_ohlcv(sym, df, meta={"source": "yahoo", "yahoo_symbol": f"{sym}.NS"})
            ok += 1
            print(f"[{i}/{len(universe)}] ok    {sym} ({len(df)} rows)", flush=True)
        except Exception as e:  # noqa: BLE001
            failed += 1
            failures.append(sym)
            print(f"[{i}/{len(universe)}] FAIL  {sym}: {str(e)[:80]}", flush=True)
        time.sleep(args.pause)

    mins = (time.time() - t0) / 60
    print(f"\nDone in {mins:.1f} min: {ok} fetched, {skipped} already cached, {failed} failed")
    if failures:
        print("Failed symbols:", ",".join(failures))


if __name__ == "__main__":
    main()
