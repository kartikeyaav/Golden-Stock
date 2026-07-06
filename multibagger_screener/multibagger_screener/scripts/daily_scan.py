"""
scripts/daily_scan.py — the daily post-close job (pipeline steps 4-6), now
EVIDENCE-ALIGNED (2026-07-06): watches the FULL universe + holdings, because
the validated system entered breakouts from the whole universe — restricting
the scan to the focus list would silently add a gate no backtest ever tested.
The focus list remains a reporting/prioritization convenience only.

  1. incremental price update (whole universe + holdings + benchmark)
  2. re-tag every watched name (mechanical stage tags)
  3. DIFF vs saved state -> transitions only:
        * -> CONFIRMED                BUY CANDIDATE (conviction card attached)
        EXTENDED -> CONFIRMED         RE-ENTRY WINDOW (card attached)
        * -> ANTICIPATION             WATCH CLOSELY (zero capital)
        holding -> BROKEN             EXIT WARNING
  4. append every alert to journal/signals_journal.csv (append-only — this
     is the forward-validation record; never edit it by hand)
  5. save state; write daily_alerts.md (the file the Telegram job sends)

    python scripts/daily_scan.py
    python scripts/daily_scan.py --no-update
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from datetime import datetime

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.cache import load_ohlcv
from data.screener_fetch import load_company
from scoring.conviction import assess
from scoring.phase_b import build_dimensions, build_vetoes, tag_archetypes
from scoring.phase_c import enrich, enrichment_dimensions
from scoring.stage_tagger import tag_stock
from scoring.technical_score import compute_atr, compute_entry_plan
from reports.watchlist_card import render_card
from fetch_fundamentals import flatten
from position_manager import check_positions
from update_prices import universe_and_holdings_symbols, update_symbols

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_STATE = os.path.join(ROOT, "state", "tags_state.json")
JOURNAL_PATH = os.path.join(ROOT, "journal", "signals_journal.csv")
JOURNAL_FIELDS = ["logged_at", "symbol", "kind", "old_tag", "new_tag", "close",
                  "atr", "stop_suggested", "conviction_score", "coverage_pct",
                  "vetoed", "veto_reasons", "rs_pctile", "archetypes"]


def health_check(today_tags: dict, symbols: list[str]) -> list[str]:
    """Silent staleness is the failure mode of autonomous systems — check the
    data actually moved and the tagger isn't degenerate; alert LOUDLY if not."""
    problems = []
    bench = load_ohlcv("NIFTY50")
    if bench is None:
        problems.append("benchmark NIFTY50 missing from cache")
    else:
        age = (datetime.now() - bench["date"].iloc[-1]).days
        if age > 5:
            problems.append(f"benchmark data is {age} days old — price feed may be broken")
    tagged_frac = len(today_tags) / max(len(symbols) - 1, 1)
    if tagged_frac < 0.80:
        problems.append(f"only {tagged_frac:.0%} of watched names tagged — data gaps?")
    if today_tags:
        counts = pd.Series(list(today_tags.values())).value_counts()
        if counts.index[0] == "WATCH" and counts.iloc[0] > 0.95 * len(today_tags):
            problems.append("tagger degenerate: >95% WATCH — indicator inputs look broken")
    return [f"!! HEALTH: {p}" for p in problems]


def load_state(path: str) -> dict | None:
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def save_state(path: str, tags: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"date": datetime.now().strftime("%Y-%m-%d"), "tags": tags}, f, indent=1)


def journal_append(rows: list[dict]) -> None:
    if not rows:
        return
    os.makedirs(os.path.dirname(JOURNAL_PATH), exist_ok=True)
    new_file = not os.path.exists(JOURNAL_PATH)
    with open(JOURNAL_PATH, "a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=JOURNAL_FIELDS)
        if new_file:
            w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in JOURNAL_FIELDS})


def market_risk_scale() -> float:
    """Regime sizing (matrix v3b, ADOPTED): half risk when NIFTY50 closes
    below its 150-DMA. Sizing only — entries are never filtered."""
    bench = load_ohlcv("NIFTY50")
    if bench is None or len(bench) < 150:
        return 1.0
    sma150 = bench["close"].rolling(150).mean().iloc[-1]
    return 0.5 if float(bench["close"].iloc[-1]) < float(sma150) else 1.0


def build_candidate(sym: str, tag_result: dict, industry: str | None,
                    rs_pctile: float | None, company_name: str = "") -> dict:
    """Conviction card + journal fields for an alerted name. Fundamentals and
    news are CONTEXT for the human (and vetoes) — never a machine gate
    (matrix v1/v2, brief section 2B). Phase C enrichment runs here, on the
    1-3 alerted names only."""
    raw = load_company(sym)
    fund_row = flatten(sym, raw) if raw else None
    dims = build_dimensions(tag_result, rs_pctile, fund_row, industry)

    news = enrich(sym, company_name or sym)
    by_key = {d.key: d for d in dims}
    for d in enrichment_dimensions(news):
        by_key[d.key] = d
    dims = list(by_key.values())

    vetoes = build_vetoes(fund_row) if fund_row else []
    conviction = assess(dims, vetoes)
    archetypes = tag_archetypes(fund_row, industry) if fund_row else None
    df = load_ohlcv(sym)
    atr = float(compute_atr(df).iloc[-1]) if df is not None else None
    plan = compute_entry_plan(tag_result["last_close"], atr=atr,
                              risk_scale=market_risk_scale()) if atr else {}
    return {
        "card": render_card(sym, tag_result, conviction, atr=atr,
                            archetypes=archetypes, dim_notes=True, news=news,
                            risk_scale=market_risk_scale()),
        "close": tag_result["last_close"],
        "atr": round(atr, 2) if atr else "",
        "stop_suggested": plan.get("stop_loss_price", ""),
        "conviction_score": conviction.score,
        "coverage_pct": conviction.coverage_pct,
        "vetoed": conviction.vetoed,
        "veto_reasons": "; ".join(conviction.veto_reasons),
        "archetypes": " + ".join(archetypes) if archetypes else "",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-update", action="store_true")
    parser.add_argument("--state-file", default=DEFAULT_STATE)
    args = parser.parse_args()

    universe = pd.read_csv(os.path.join(ROOT, "universe.csv"))
    industry_by_sym = dict(zip(universe["symbol"], universe["industry"]))
    company_by_sym = dict(zip(universe["symbol"], universe["company"]))
    focus_path = os.path.join(ROOT, "focus_list.csv")
    rs_by_sym = {}
    if os.path.exists(focus_path):
        focus = pd.read_csv(focus_path)
        rs_by_sym = dict(zip(focus["symbol"], focus["rs_pctile"]))
    holdings = set()
    holdings_path = os.path.join(ROOT, "holdings.csv")
    if os.path.exists(holdings_path):
        holdings = set(pd.read_csv(holdings_path)["symbol"])
    positions_path = os.path.join(ROOT, "positions.csv")
    if os.path.exists(positions_path):
        holdings |= set(pd.read_csv(positions_path)["symbol"])

    symbols = universe_and_holdings_symbols(ROOT)
    if not args.no_update:
        print(f"updating prices for {len(symbols)} symbols...", flush=True)
        update_symbols(symbols, pause=0.25)

    bench = load_ohlcv("NIFTY50")
    today_tags: dict[str, str] = {}
    tag_results: dict[str, dict] = {}
    for sym in symbols:
        if sym == "NIFTY50":
            continue
        df = load_ohlcv(sym)
        if df is None or len(df) < 260:
            continue
        t = tag_stock(df, bench)
        today_tags[sym] = t["tag"]
        tag_results[sym] = t

    prev = load_state(args.state_file)
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [f"# Daily scan — {now}", ""]
    cards: list[str] = []
    journal_rows: list[dict] = []

    if prev is None:
        lines.append(f"Baseline established for {len(today_tags)} names — no alerts on first run.")
        counts = pd.Series(list(today_tags.values())).value_counts().to_dict()
        lines.append(f"Tag counts: {counts}")
    else:
        prev_tags = prev.get("tags", {})
        alerts, infos = [], []
        for sym, new in today_tags.items():
            old = prev_tags.get(sym)
            if old is None or old == new:
                continue
            if new == "CONFIRMED":
                kind = "RE-ENTRY WINDOW" if old == "EXTENDED" else "BUY CANDIDATE"
            elif new == "ANTICIPATION":
                kind = "WATCH CLOSELY"
            elif new == "BROKEN" and sym in holdings:
                kind = "EXIT WARNING"
            else:
                infos.append((sym, old, new))
                continue
            alerts.append((kind, sym, old, new))

        if not alerts:
            lines.append(f"No transitions among {len(today_tags)} watched names. "
                         f"({len(infos)} minor tag shifts.)")
        else:
            lines.append(f"{len(alerts)} alert(s):")
            lines.append("")
            for kind, sym, old, new in alerts:
                lines.append(f"- **{kind}**: {sym}  ({old} -> {new})")
                row = {"logged_at": now, "symbol": sym, "kind": kind,
                       "old_tag": old, "new_tag": new,
                       "rs_pctile": rs_by_sym.get(sym, "")}
                if kind in ("BUY CANDIDATE", "RE-ENTRY WINDOW"):
                    cand = build_candidate(sym, tag_results[sym],
                                           industry_by_sym.get(sym), rs_by_sym.get(sym),
                                           company_name=company_by_sym.get(sym, sym))
                    cards.append(cand.pop("card"))
                    row.update(cand)
                else:
                    row["close"] = tag_results[sym]["last_close"]
                journal_rows.append(row)
        if infos:
            lines.append("")
            lines.append("Minor shifts: " + ", ".join(f"{s} {o}->{n}" for s, o, n in infos))

    # position management: track every open position against ITS OWN plan
    pos_alerts, pos_journal = check_positions()
    if pos_alerts:
        lines.append("")
        lines.append(f"{len(pos_alerts)} position-management alert(s):")
        lines += pos_alerts
        journal_rows += pos_journal

    # health checks go on TOP so a broken feed can't hide behind "no transitions"
    problems = health_check(today_tags, symbols)
    if problems:
        lines = lines[:2] + problems + [""] + lines[2:]

    save_state(args.state_file, today_tags)
    journal_append(journal_rows)

    report = "\n".join(lines)
    if cards:
        report += "\n\n## Cards\n\n```\n" + "\n".join(cards) + "\n```\n"
    out_path = os.path.join(ROOT, "daily_alerts.md")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(report)
    print(f"\n-> {out_path}")
    if journal_rows:
        print(f"-> {len(journal_rows)} row(s) appended to {JOURNAL_PATH}")


if __name__ == "__main__":
    main()
