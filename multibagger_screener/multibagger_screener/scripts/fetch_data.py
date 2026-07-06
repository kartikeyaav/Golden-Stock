"""
scripts/fetch_data.py — CLI backfill: Yahoo -> local cache.

    python scripts/fetch_data.py SUZLON.NS BSE.NS ^NSEI --start 2019-01-01

Cache names are derived automatically (SUZLON.NS -> SUZLON, ^NSEI -> NIFTY50)
or pass explicit pairs with '=':  NIFTY50=^NSEI
"""

from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.yahoo_loader import fetch_and_cache

_INDEX_NAMES = {"^NSEI": "NIFTY50", "^BSESN": "SENSEX"}


def cache_name_for(yahoo_symbol: str) -> str:
    if yahoo_symbol in _INDEX_NAMES:
        return _INDEX_NAMES[yahoo_symbol]
    return yahoo_symbol.replace(".NS", "").replace(".BO", "").replace("^", "IDX_")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("symbols", nargs="+",
                        help="Yahoo symbols (SUZLON.NS) or CACHE=YAHOO pairs (NIFTY50=^NSEI)")
    parser.add_argument("--start", default="2019-01-01")
    parser.add_argument("--end", default=None)
    args = parser.parse_args()

    failures = []
    for spec in args.symbols:
        if "=" in spec:
            cache_symbol, yahoo_symbol = spec.split("=", 1)
        else:
            yahoo_symbol = spec
            cache_symbol = cache_name_for(spec)
        try:
            n = fetch_and_cache(cache_symbol, yahoo_symbol, args.start, args.end)
            print(f"[ok]   {cache_symbol:<12} <- {yahoo_symbol:<12} {n} rows")
        except Exception as e:  # noqa: BLE001 — report and continue the batch
            failures.append(spec)
            print(f"[FAIL] {cache_symbol:<12} <- {yahoo_symbol:<12} {e}")

    if failures:
        print(f"\n{len(failures)} failure(s): {failures}")
        sys.exit(1)


if __name__ == "__main__":
    main()
