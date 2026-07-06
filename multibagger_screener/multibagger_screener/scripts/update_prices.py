"""
scripts/update_prices.py — incremental price updates for cached symbols:
fetch only from (last cached date - 7d) to now and merge into the cache
(cache.save_ohlcv dedupes). Symbols not yet cached get a full backfill.

    python scripts/update_prices.py --focus       # focus list + holdings + benchmark
    python scripts/update_prices.py --all         # whole universe.csv
    python scripts/update_prices.py SUZLON BSE    # explicit
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from datetime import datetime, timedelta

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.cache import load_manifest
from data.yahoo_loader import fetch_yahoo_daily
from data.cache import save_ohlcv

FULL_BACKFILL_START = "2019-01-01"
_SPECIAL_YAHOO = {"NIFTY50": "^NSEI"}


def update_symbols(symbols: list[str], pause: float = 0.3) -> tuple[int, list[str]]:
    manifest = load_manifest()
    ok, failures = 0, []
    for i, sym in enumerate(symbols, 1):
        yahoo_sym = _SPECIAL_YAHOO.get(sym) or manifest.get(sym, {}).get("yahoo_symbol") or f"{sym}.NS"
        last = manifest.get(sym, {}).get("last_date")
        start = (datetime.strptime(last, "%Y-%m-%d") - timedelta(days=7)).strftime("%Y-%m-%d") \
            if last else FULL_BACKFILL_START
        try:
            df = fetch_yahoo_daily(yahoo_sym, start)
            save_ohlcv(sym, df, meta={"source": "yahoo", "yahoo_symbol": yahoo_sym})
            ok += 1
        except Exception as e:  # noqa: BLE001
            failures.append(sym)
            print(f"[{i}/{len(symbols)}] FAIL {sym}: {str(e)[:60]}", flush=True)
        if i % 50 == 0:
            print(f"[{i}/{len(symbols)}] ...", flush=True)
        time.sleep(pause)
    return ok, failures


def universe_and_holdings_symbols(root: str) -> list[str]:
    """The FULL watch set. Matrix evidence (2026-07-06): the validated system
    entered breakouts from the whole universe — the daily scan must watch the
    whole universe too, or the focus-list filter becomes an untested gate."""
    symbols = ["NIFTY50"]
    universe_path = os.path.join(root, "universe.csv")
    if os.path.exists(universe_path):
        symbols += pd.read_csv(universe_path)["symbol"].tolist()
    holdings_path = os.path.join(root, "holdings.csv")
    if os.path.exists(holdings_path):
        symbols += pd.read_csv(holdings_path)["symbol"].tolist()
    seen, out = set(), []
    for s in symbols:
        if s not in seen:
            seen.add(s)
            out.append(s)
    return out


def focus_and_holdings_symbols(root: str) -> list[str]:
    symbols = ["NIFTY50"]
    focus_path = os.path.join(root, "focus_list.csv")
    if os.path.exists(focus_path):
        symbols += pd.read_csv(focus_path)["symbol"].tolist()
    holdings_path = os.path.join(root, "holdings.csv")
    if os.path.exists(holdings_path):
        symbols += pd.read_csv(holdings_path)["symbol"].tolist()
    seen, out = set(), []
    for s in symbols:
        if s not in seen:
            seen.add(s)
            out.append(s)
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("symbols", nargs="*")
    parser.add_argument("--focus", action="store_true")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--pause", type=float, default=0.3)
    args = parser.parse_args()

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if args.all:
        symbols = ["NIFTY50"] + pd.read_csv(os.path.join(root, "universe.csv"))["symbol"].tolist()
    elif args.focus:
        symbols = focus_and_holdings_symbols(root)
    else:
        symbols = args.symbols
    if not symbols:
        parser.error("give symbols, --focus, or --all")

    t0 = time.time()
    ok, failures = update_symbols(symbols, pause=args.pause)
    print(f"updated {ok}/{len(symbols)} in {(time.time()-t0)/60:.1f} min"
          + (f"; failed: {failures}" if failures else ""))


if __name__ == "__main__":
    main()
