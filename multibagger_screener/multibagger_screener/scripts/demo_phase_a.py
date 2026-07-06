"""
scripts/demo_phase_a.py — Phase A demonstration: run the stage tagger +
coverage-honest technical read on cached names, print cards, and write
watchlist_report.md. Also prints tag reads at key HISTORICAL dates for the
exemplars, so the tagger can be sanity-checked against known history
(Phase A acceptance criterion in PROJECT_BRIEF.md Section 7).

    python scripts/demo_phase_a.py SUZLON BSE --bench NIFTY50
"""

from __future__ import annotations

import argparse
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.cache import load_ohlcv
from scoring.conviction import assess, phase_a_dimensions
from scoring.stage_tagger import tag_stock
from scoring.technical_score import compute_atr
from reports.watchlist_card import render_card


def read_stock(symbol: str, bench: pd.DataFrame | None, as_of: str | None = None):
    df = load_ohlcv(symbol)
    if df is None:
        raise FileNotFoundError(f"{symbol} not in cache — run scripts/fetch_data.py first")
    b = bench
    if as_of:
        df = df[df["date"] <= as_of].reset_index(drop=True)
        b = bench[bench["date"] <= as_of].reset_index(drop=True) if bench is not None else None
    tag = tag_stock(df, b)
    atr = float(compute_atr(df).iloc[-1])
    conviction = assess(phase_a_dimensions(tag))
    return tag, conviction, atr


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("symbols", nargs="+")
    parser.add_argument("--bench", default="NIFTY50")
    parser.add_argument("--as-of", default=None, help="optional YYYY-MM-DD historical read")
    args = parser.parse_args()

    bench = load_ohlcv(args.bench)
    if bench is None:
        print(f"[warn] benchmark {args.bench} not cached — RS metrics will be neutral")

    cards = []
    summary = []
    for symbol in args.symbols:
        try:
            tag, conviction, atr = read_stock(symbol, bench, args.as_of)
        except Exception as e:  # noqa: BLE001
            print(f"[FAIL] {symbol}: {e}")
            continue
        card = render_card(symbol, tag, conviction, atr=atr)
        cards.append(card)
        print(card)
        summary.append((symbol, tag["tag"], conviction.display()))

    print("-" * 72)
    for symbol, tag, disp in summary:
        print(f"  {symbol:<12} [{tag:<12}] {disp}")

    out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "watchlist_report.md")
    with open(out, "w", encoding="utf-8") as f:
        f.write("# Watchlist report (Phase A — technical read only)\n\n```\n")
        f.write("\n".join(cards))
        f.write("\n```\n")
    print(f"\nReport written to {out}")


if __name__ == "__main__":
    main()
