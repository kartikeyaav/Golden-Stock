"""
scripts/run_shortlist.py — the full Phase A+B read on the current shortlist:
stage tags (price) + fundamentals (screener cache) + vetoes + archetypes
-> coverage-honest conviction ranking. Writes shortlist_report.md.

    python scripts/run_shortlist.py            # CONFIRMED + ANTICIPATION
    python scripts/run_shortlist.py --cards 10 # detailed cards for top N
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.cache import load_ohlcv
from scoring.conviction import assess
from scoring.phase_b import build_dimensions, build_vetoes, tag_archetypes
from scoring.phase_c import enrich, enrichment_dimensions
from scoring.stage_tagger import tag_stock
from scoring.technical_score import compute_atr, compute_entry_plan
from reports.watchlist_card import render_card


def market_risk_scale() -> float:
    """Regime sizing (matrix v3b): half risk when NIFTY50 < its 150-DMA."""
    bench = load_ohlcv("NIFTY50")
    if bench is None or len(bench) < 150:
        return 1.0
    sma150 = bench["close"].rolling(150).mean().iloc[-1]
    return 0.5 if float(bench["close"].iloc[-1]) < float(sma150) else 1.0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cards", type=int, default=8)
    parser.add_argument("--no-news", action="store_true",
                        help="skip per-stock news enrichment (faster)")
    args = parser.parse_args()

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    focus = pd.read_csv(os.path.join(root, "focus_list.csv"))
    shortlist = focus[focus["tag"].isin(["CONFIRMED", "ANTICIPATION"])]
    funds = pd.read_csv(os.path.join(root, "fundamentals_flat.csv"))
    funds_by_sym = {r["symbol"]: r.to_dict() for _, r in funds.iterrows()}
    universe = pd.read_csv(os.path.join(root, "universe.csv"))
    company_by_sym = dict(zip(universe["symbol"], universe["company"]))
    bench = load_ohlcv("NIFTY50")
    risk_scale = market_risk_scale()

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

        # Phase C: news/filings feed the theme + catalyst dimensions here too
        # (previously only alert cards got this — the ranking fetched news but
        # scored those dims as "no data": inconsistent, fixed 2026-07-07)
        news_e = None
        if not args.no_news:
            news_e = enrich(sym, company_by_sym.get(sym, sym))
            time.sleep(0.3)
            if news_e.get("ok"):
                by_key = {d.key: d for d in dims}
                for d2 in enrichment_dimensions(news_e):
                    by_key[d2.key] = d2
                dims = list(by_key.values())

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
            "_archetype_list": archetypes, "_news": news_e,
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

    # per-stock detail for the dashboard drawer: WHY each score is what it is
    # (dimension breakdown with notes), the sized entry plan (regime-scaled),
    # and news/catalyst context. This is what makes the UI explain itself.
    print(f"\nbuilding shortlist_details.json "
          f"({'no news' if args.no_news else 'with news enrichment'})...", flush=True)
    details = {}
    for i, (_, r) in enumerate(out.iterrows(), 1):
        sym = r["symbol"]
        conv = r["_conviction"]
        tag = r["_tag_result"]

        news_blob = None
        if not args.no_news:
            e = r.get("_news") or {}
            if e.get("ok"):
                news_blob = {
                    "count": e["headline_count"],
                    "themes": e["themes"], "events": e["events"],
                    "red_flags": e["red_flags"],
                    "filings": [{"d": str(f.get("date", ""))[:10], "t": f["subject"][:110]}
                                for f in e.get("filings", [])[:3]],
                    "headlines": [{"d": h["date"].strftime("%d %b"), "t": h["text"][:110],
                                   "s": h["source"]} for h in e.get("headlines", [])[:4]],
                }

        plan = {}
        if r["tag"] == "CONFIRMED" and not r["vetoed"]:
            p = compute_entry_plan(tag["last_close"], atr=r["_atr"], risk_scale=risk_scale)
            if not p.get("skip"):
                keys = ("entry_price", "stop_loss_price", "risk_per_share", "shares_total",
                        "shares_trading_lot", "shares_core_lot", "position_value",
                        "capital_at_risk", "risk_scale")
                plan = {k: p[k] for k in keys if k in p}
                plan["breakeven_trigger"] = p.get("breakeven_move_trigger_price")
                plan["partial_price"] = round(p["entry_price"] + p["risk_per_share"] * 2.5, 2)

        details[sym] = {
            "reasons": tag.get("reasons", []),
            "stage_name": tag.get("stage", {}).get("stage_name", ""),
            "tt_checks": tag.get("trend_template_checks_passed", 0),
            "vcp": tag.get("vcp_valid", False),
            "dims": [{"k": d["key"], "w": d["weight"], "s": d["score"],
                      "live": d["live"], "n": d["notes"][:220]}
                     for d in conv.per_dimension],
            "veto_reasons": conv.veto_reasons,
            "plan": plan,
            "news": news_blob,
        }
        if i % 20 == 0:
            print(f"  details {i}/{len(out)}", flush=True)

    with open(os.path.join(root, "shortlist_details.json"), "w", encoding="utf-8") as fh:
        json.dump(details, fh, default=str)
    print(f"details -> shortlist_details.json ({len(details)} stocks)")


if __name__ == "__main__":
    main()
