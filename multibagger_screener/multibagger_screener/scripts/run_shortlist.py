"""
scripts/run_shortlist.py — the full Phase A+B read on the current shortlist:
stage tags (price) + fundamentals (screener cache) + vetoes + archetypes
-> coverage-honest conviction ranking. Writes shortlist_report.md.

    python scripts/run_shortlist.py            # CONFIRMED + ANTICIPATION
    python scripts/run_shortlist.py --cards 10 # detailed cards for top N
"""

from __future__ import annotations

import argparse
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.cache import load_ohlcv
from scoring.conviction import assess
from scoring.phase_b import build_dimensions, build_vetoes, tag_archetypes
from scoring.stage_tagger import tag_stock
from scoring.technical_score import compute_atr
from reports.watchlist_card import render_card


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cards", type=int, default=8)
    args = parser.parse_args()

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    focus = pd.read_csv(os.path.join(root, "focus_list.csv"))
    shortlist = focus[focus["tag"].isin(["CONFIRMED", "ANTICIPATION"])]
    funds = pd.read_csv(os.path.join(root, "fundamentals_flat.csv"))
    funds_by_sym = {r["symbol"]: r.to_dict() for _, r in funds.iterrows()}
    bench = load_ohlcv("NIFTY50")

    results = []
    for _, f in shortlist.iterrows():
        sym = f["symbol"]
        df = load_ohlcv(sym)
        if df is None:
            continue
        tag = tag_stock(df, bench)
        fund_row = funds_by_sym.get(sym)
        industry = f.get("industry")

        dims = build_dimensions(tag, f.get("rs_pctile"), fund_row, industry)
        vetoes = build_vetoes(fund_row) if fund_row else []
        conviction = assess(dims, vetoes)
        atr = float(compute_atr(df).iloc[-1])
        archetypes = tag_archetypes(fund_row, industry) if fund_row else None

        results.append({
            "symbol": sym, "industry": industry, "tag": tag["tag"],
            "archetypes": " + ".join(archetypes) if archetypes else "",
            "score": conviction.score, "coverage": conviction.coverage_pct,
            "label": conviction.label, "vetoed": conviction.vetoed,
            "veto_reasons": "; ".join(conviction.veto_reasons),
            "_tag_result": tag, "_conviction": conviction, "_atr": atr,
            "_archetype_list": archetypes,
        })

    out = pd.DataFrame(results).sort_values(
        ["vetoed", "score"], ascending=[True, False]).reset_index(drop=True)

    display_cols = ["symbol", "industry", "tag", "archetypes", "score", "coverage",
                    "label", "vetoed"]
    print(f"\n=== RANKED SHORTLIST ({len(out)}) ===")
    print(out[display_cols].head(25).to_string(index=False))

    vetoed = out[out["vetoed"]]
    if not vetoed.empty:
        print(f"\n=== VETOED ({len(vetoed)}) ===")
        print(vetoed[["symbol", "tag", "score", "veto_reasons"]].to_string(index=False))

    # detailed cards for the top N non-vetoed
    top = out[~out["vetoed"]].head(args.cards)
    cards = [render_card(r["symbol"], r["_tag_result"], r["_conviction"],
                         atr=r["_atr"], archetypes=r["_archetype_list"], dim_notes=True)
             for _, r in top.iterrows()]

    report_path = os.path.join(root, "shortlist_report.md")
    with open(report_path, "w", encoding="utf-8") as fh:
        fh.write("# Shortlist report — Phase A+B (price + fundamentals)\n\n")
        fh.write("```\n" + out[display_cols + ["veto_reasons"]].to_string(index=False) + "\n```")
        fh.write("\n\n## Top cards\n\n```\n")
        fh.write("\n".join(cards))
        fh.write("\n```\n")
    print(f"\nreport -> {report_path}")

    out[display_cols + ["veto_reasons"]].to_csv(
        os.path.join(root, "shortlist_ranked.csv"), index=False)


if __name__ == "__main__":
    main()
