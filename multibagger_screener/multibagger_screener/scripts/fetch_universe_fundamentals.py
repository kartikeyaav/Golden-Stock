"""
scripts/fetch_universe_fundamentals.py — ONE-TIME pull of screener.in pages
for the whole universe.csv, to enable the point-in-time (PIT) backtest of the
fundamental dimensions (each page carries ~12 quarters of results + ~10 years
of balance sheet/shareholding — the raw material for "what was known when").

Manners: extra-polite pause (default 2.2s), skips anything already cached,
never re-fetches (weekly refresh only touches the shortlist). This is a
one-time research backfill, not a recurring scrape.

    python scripts/fetch_universe_fundamentals.py
"""

from __future__ import annotations

import argparse
import os
import sys
import time

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.screener_fetch import fetch_company, load_company, save_company


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pause", type=float, default=2.2)
    args = parser.parse_args()

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    universe = pd.read_csv(os.path.join(root, "universe.csv"))

    todo = [s for s in universe["symbol"] if load_company(s) is None]
    print(f"universe {len(universe)}, already cached {len(universe) - len(todo)}, "
          f"fetching {len(todo)} (pause {args.pause}s)", flush=True)

    ok, failed = 0, []
    t0 = time.time()
    for i, sym in enumerate(todo, 1):
        try:
            save_company(sym, fetch_company(sym))
            ok += 1
        except Exception as e:  # noqa: BLE001
            failed.append(sym)
            print(f"[{i}/{len(todo)}] FAIL {sym}: {str(e)[:60]}", flush=True)
        if i % 25 == 0:
            print(f"[{i}/{len(todo)}] ok={ok} ({(time.time()-t0)/60:.1f} min)", flush=True)
        time.sleep(args.pause)

    print(f"\nDone in {(time.time()-t0)/60:.1f} min: {ok} fetched, {len(failed)} failed")
    if failed:
        print("Failed:", ",".join(failed))


if __name__ == "__main__":
    main()
