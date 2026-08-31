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
from datetime import datetime

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.cache import load_ohlcv
from scoring.conviction import assess
from scoring.phase_b import build_dimensions, build_vetoes, tag_archetypes
from scoring.phase_c import card_news_blob, enrich, enrichment_dimensions
from scoring.stage_tagger import tag_stock
from scoring.technical_score import compute_atr, compute_entry_plan
from reports.watchlist_card import render_card


from scoring.regime import market_risk_scale


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
    # Daily delivery percentage, merged onto the quarterly fundamentals row so
    # score_smart_money sees one dict and phase_b's contract stays unchanged.
    # Absent file = the dimension simply says so; it is never fabricated.
    dpath = os.path.join(root, "delivery_stats.csv")
    if os.path.exists(dpath):
        for _, dr in pd.read_csv(dpath).iterrows():
            row = funds_by_sym.get(dr["symbol"])
            if row is not None:
                row.update({k: dr[k] for k in
                            ("deliv_med", "deliv_recent", "deliv_trend_pp")
                            if k in dr})
    universe = pd.read_csv(os.path.join(root, "universe.csv"))
    company_by_sym = dict(zip(universe["symbol"], universe["company"]))
    bench = load_ohlcv("NIFTY50")
    risk_scale = market_risk_scale()

    # Rebuild the policy radar before enriching anything (2026-08-28). The
    # nightly scan builds it too, but the weekly runs on its own checkout and
    # macro_radar.load() treats a file older than MAX_AGE_DAYS as absent —
    # without this, every weekly card would read "policy radar unavailable"
    # whenever the daily commit was more than a few days back. Cheap: it reads
    # the archive already on disk and fetches nothing.
    if not args.no_news:
        try:
            from data.macro_radar import scan_macro
            _mr = scan_macro()
            if _mr.get("ok"):
                print(f"policy radar: {_mr['policy_hits']} government/"
                      f"regulatory events -> {_mr['stories']} stories across "
                      f"{len(_mr['themes'])} themes", flush=True)
        except Exception as e:                     # noqa: BLE001 — never kill the refresh
            print(f"policy radar failed ({str(e)[:70]})", flush=True)

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
            news_e = enrich(sym, company_by_sym.get(sym, sym), industry or "")
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

    # detailed cards for the top N non-vetoed (same regime sizing as dashboard)
    top = out[~out["vetoed"]].head(args.cards)
    cards = [render_card(r["symbol"], r["_tag_result"], r["_conviction"],
                         atr=r["_atr"], archetypes=r["_archetype_list"],
                         dim_notes=True, risk_scale=risk_scale)
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
            news_blob = card_news_blob(r.get("_news") or {})

        plan = {}
        if r["tag"] == "CONFIRMED" and not r["vetoed"]:
            p = compute_entry_plan(tag["last_close"], atr=r["_atr"], risk_scale=risk_scale)
            if not p.get("skip"):
                keys = ("entry_price", "stop_loss_price", "risk_per_share", "shares_total",
                        "shares_trading_lot", "shares_core_lot", "position_value",
                        "capital_at_risk", "risk_scale")
                plan = {k: p[k] for k in keys if k in p}
                plan["breakeven_trigger"] = p.get("breakeven_move_trigger_price")
                plan["partial_price"] = p.get("partial_profit_price")

        details[sym] = {
            # same top-level schema as alert_details.json so the dashboard
            # can compare vintages coverage-aware instead of blindly letting
            # a stale fundamentals-blind alert snapshot mask this richer
            # weekly read (SHILPAMED incoherence, user-caught 2026-07-19)
            "score": conv.score, "coverage": conv.coverage_pct,
            "label": conv.label,
            "scored_at": datetime.now().strftime("%Y-%m-%d"),
            "reasons": tag.get("reasons", []),
            "stage_name": tag.get("stage", {}).get("stage_name", ""),
            "tt_checks": tag.get("trend_template_checks_passed", 0),
            "vcp": tag.get("vcp_valid", False),
            # VCP breakout pivot for the drawer chart geometry (display only);
            # kept in parity with daily_scan.build_candidate's detail blob.
            # Old blobs without this key null-guard fine in the JS.
            "pivot_price": tag.get("pivot_price"),
            "dims": [{"k": d["key"], "w": d["weight"], "s": d["score"],
                      "live": d["live"], "n": d["notes"][:220]}
                     for d in conv.per_dimension],
            "veto_reasons": conv.veto_reasons,
            "plan": plan,
            "news": news_blob,
        }
        if i % 20 == 0:
            print(f"  details {i}/{len(out)}", flush=True)

    # ------------------------------------------------------------------
    # EVERY OTHER focus name that has fundamentals on disk gets a scored
    # detail too.
    #
    # The bug this closes (user-reported 2026-08-02, "HFCL showed scores
    # until yesterday and today some of the scores are empty"): details were
    # built ONLY for names tagged CONFIRMED or ANTICIPATION this week. HFCL
    # was CONFIRMED last week and is not this week, so it left the file — and
    # the dashboard, finding no weekly read, fell back to its alert blob of
    # 2026-07-17, whose five fundamental dimensions are null because the name
    # was not in the shortlist when that alert fired. The score panel went
    # blank for a stock whose complete fundamentals were sitting in
    # fundamentals_flat.csv the whole time. 27 names left the shortlist in
    # this week's refresh alone, so this was never about one stock.
    #
    # A tag is a statement about the CHART. It was never a reason to stop
    # knowing what a company earns. News enrichment stays on the ranked
    # shortlist — that is the network cost, and these dimensions are read
    # from a local CSV.
    scored_syms = set(details)
    extra = 0
    # The focus list, PLUS every name the nightly scan tags. The screener
    # renders a row per tagged name; scoring stopping at the focus list left
    # 328 of 618 rows with a dash in the conviction column while 327 of them
    # had real cached fundamentals sitting on disk (measured 2026-08-03).
    #
    # News is the one thing that stays scoped to the focus list: it is the
    # network cost, and taking it universe-wide would add ~35 minutes to the
    # weekly job. Names scored without it carry an explicit note saying the
    # conviction number is a partial-coverage read — see newsSection() — so a
    # 75%-coverage score is never presented as if it were a full one.
    focus_rows = {r["symbol"]: r for _, r in focus.iterrows()}
    industry_by_sym = dict(zip(universe["symbol"], universe.get("industry", universe["symbol"])))
    wider = list(dict.fromkeys(list(focus_rows) + sorted(funds_by_sym)))
    for sym in wider:
        f = focus_rows.get(sym, {"symbol": sym, "rs_pctile": None,
                                 "industry": industry_by_sym.get(sym)})
        if sym in scored_syms:
            continue
        fund_row = funds_by_sym.get(sym)
        if not fund_row:
            continue                       # no fundamentals = nothing to add
        df = load_ohlcv(sym)
        if df is None:
            continue
        tag = tag_stock(df, bench)
        industry = f.get("industry")
        dims = build_dimensions(tag, f.get("rs_pctile"), fund_row, industry)

        # NEWS FOR THESE NAMES TOO (2026-08-03, user-reported).
        #
        # The first version of this pass scored them from fundamentals and set
        # news=None, on the reasoning that enrichment is the network cost. That
        # left a seam the user found immediately: GESHIP and POWERINDIA carry
        # conviction scores of 83.8 and 82.7 with no News & filings panel at
        # all, and FEDERALBNK shows a news panel (riding along from an older
        # alert blob) beside a catalyst dimension reading "no data" — a card
        # contradicting itself.
        #
        # Scoring 280 names while reading news for 99 is not a coverage
        # trade-off, it is two different systems sharing a drawer. The extra
        # ~180 fetches cost roughly 20 minutes on a WEEKLY job with a 180-minute
        # budget, and they buy coherence plus 100% coverage on every scored name.
        # WHY a name has no news is a different fact from the fact that it
        # has none, and the card has to be able to say which. Three distinct
        # cases, recorded rather than inferred:
        news_e = None
        if args.no_news:
            news_status = "skipped: this run was built without news"
        elif sym not in focus_rows:
            news_status = ("not fetched: outside this week's focus list, and "
                           "news is read only for focus names to bound the "
                           "weekly job")
        else:
            news_e = enrich(sym, company_by_sym.get(sym, sym), industry or "")
            time.sleep(0.3)
            if news_e.get("ok"):
                news_status = "read"
                by_key = {d.key: d for d in dims}
                for d2 in enrichment_dimensions(news_e):
                    by_key[d2.key] = d2
                dims = list(by_key.values())
            elif news_e.get("blind"):
                news_status = "unavailable: every news source was unreachable"
            else:
                news_status = f"unavailable: {str(news_e.get('error') or '')[:70]}"

        conv = assess(dims, build_vetoes(fund_row))
        details[sym] = {
            "score": conv.score, "coverage": conv.coverage_pct,
            "label": conv.label,
            "scored_at": datetime.now().strftime("%Y-%m-%d"),
            "reasons": tag.get("reasons", []),
            "stage_name": tag.get("stage", {}).get("stage_name", ""),
            "tt_checks": tag.get("trend_template_checks_passed", 0),
            "vcp": tag.get("vcp_valid", False),
            "pivot_price": tag.get("pivot_price"),
            "dims": [{"k": d["key"], "w": d["weight"], "s": d["score"],
                      "live": d["live"], "n": d["notes"][:220]}
                     for d in conv.per_dimension],
            "veto_reasons": conv.veto_reasons,
            "plan": {},                    # not CONFIRMED — no mechanical plan
            "news": card_news_blob(news_e or {}),
            "news_status": news_status,
            "in_focus": sym in focus_rows,
        }
        extra += 1
        if extra % 25 == 0:
            print(f"  off-shortlist {extra} scored", flush=True)
    print(f"  + {extra} off-shortlist focus names scored"
          f"{'' if args.no_news else ' (with news)'}")

    with open(os.path.join(root, "shortlist_details.json"), "w", encoding="utf-8") as fh:
        json.dump(details, fh, default=str)
    print(f"details -> shortlist_details.json ({len(details)} stocks)")


if __name__ == "__main__":
    main()
