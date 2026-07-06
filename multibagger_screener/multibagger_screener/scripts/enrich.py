"""
scripts/enrich.py — on-demand Phase A+B+C card for any symbol: stage tag +
fundamentals + live news enrichment. The "tell me about this stock right
now" command.

    python scripts/enrich.py CHENNPETRO SUZLON
"""

from __future__ import annotations

import argparse
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.cache import load_ohlcv
from scoring.stage_tagger import tag_stock
from daily_scan import build_candidate  # scripts/ is on sys.path

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("symbols", nargs="+")
    args = parser.parse_args()

    universe = pd.read_csv(os.path.join(ROOT, "universe.csv"))
    industry_by_sym = dict(zip(universe["symbol"], universe["industry"]))
    company_by_sym = dict(zip(universe["symbol"], universe["company"]))
    focus_path = os.path.join(ROOT, "focus_list.csv")
    rs_by_sym = {}
    if os.path.exists(focus_path):
        focus = pd.read_csv(focus_path)
        rs_by_sym = dict(zip(focus["symbol"], focus["rs_pctile"]))
    bench = load_ohlcv("NIFTY50")

    for sym in args.symbols:
        df = load_ohlcv(sym)
        if df is None:
            print(f"[{sym}] not in price cache — run scripts/update_prices.py {sym}")
            continue
        tag = tag_stock(df, bench)
        cand = build_candidate(sym, tag, industry_by_sym.get(sym),
                               rs_by_sym.get(sym),
                               company_name=company_by_sym.get(sym, sym))
        print(cand["card"])


if __name__ == "__main__":
    main()
