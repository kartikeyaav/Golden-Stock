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
import time
from datetime import datetime, timedelta

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.cache import load_ohlcv
from data.screener_fetch import fetch_company, load_company, save_company
from scoring.conviction import assess
from scoring.phase_b import build_dimensions, build_vetoes, tag_archetypes
from scoring.phase_c import enrich, enrichment_dimensions
from scoring.stage_tagger import tag_stock
from scoring.technical_score import compute_atr, compute_entry_plan
from reports.watchlist_card import render_card
from scoring.regime import market_risk_scale
from fetch_fundamentals import _age_days, flatten
from position_manager import check_positions
from sync_positions import check as sync_check
from update_prices import universe_and_holdings_symbols, update_symbols

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_STATE = os.path.join(ROOT, "state", "tags_state.json")
JOURNAL_PATH = os.path.join(ROOT, "journal", "signals_journal.csv")
JOURNAL_FIELDS = ["logged_at", "symbol", "kind", "old_tag", "new_tag", "close",
                  "atr", "stop_suggested", "conviction_score", "coverage_pct",
                  "vetoed", "veto_reasons", "rs_pctile", "archetypes"]

# Separate, additive record of entry FIDELITY per buy alert — kept out of the
# pristine signals_journal so we can later ask "did the alerts that were exact
# backtested triggers (VALIDATED) outperform the CONFIRMED-but-no-breakout
# ones?" without ever having gated the alerts on it. Own schema, own file.
ENTRY_SIGNALS_PATH = os.path.join(ROOT, "journal", "entry_signals.csv")
ENTRY_SIGNALS_FIELDS = ["logged_at", "symbol", "kind", "entry_status",
                        "validated_entry", "close", "pivot_price",
                        "breakout_today", "breakout_volume_ratio", "vcp_valid"]


def health_check(today_tags: dict, symbols: list[str],
                 extra_problems: list[str] | None = None) -> list[str]:
    """Silent staleness is the failure mode of autonomous systems — check the
    data actually moved, the tagger isn't degenerate, the screener parser
    still parses, and the filings feed still answers. Alert LOUDLY if not."""
    problems = list(extra_problems or [])
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
    # screener parser health (written by the weekly fundamentals job)
    ph_path = os.path.join(ROOT, "state", "parser_health.json")
    if os.path.exists(ph_path):
        try:
            ph = json.load(open(ph_path, encoding="utf-8"))
            if not ph.get("ok", True):
                problems.append(
                    f"screener parser degraded: {ph.get('empty_quarters')}/"
                    f"{ph.get('fetched')} pages parsed empty, "
                    f"{ph.get('fetch_failures')} failures — page layout may have changed")
            age_d = (datetime.now() - datetime.fromisoformat(ph["checked_at"])).days
            if age_d > 14:
                problems.append(f"fundamentals last refreshed {age_d}d ago — weekly job may be dead")
        except (ValueError, KeyError):
            pass
    return [f"!! HEALTH: {p}" for p in problems]


def load_state(path: str) -> dict | None:
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def save_state(path: str, tags: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    payload = {"date": datetime.now().strftime("%Y-%m-%d"), "tags": tags}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=1)
    # daily snapshot (audit trail for missed-day/late transitions), keep 90
    hist_dir = os.path.join(os.path.dirname(path), "history")
    os.makedirs(hist_dir, exist_ok=True)
    snap = os.path.join(hist_dir, f"{payload['date']}.json")
    with open(snap, "w", encoding="utf-8") as f:
        json.dump(payload, f)
    snaps = sorted(os.listdir(hist_dir))
    for old in snaps[:-90]:
        os.remove(os.path.join(hist_dir, old))


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


def entry_signals_append(rows: list[dict]) -> None:
    """Append entry-fidelity rows (buy/re-entry alerts only). Additive file."""
    if not rows:
        return
    os.makedirs(os.path.dirname(ENTRY_SIGNALS_PATH), exist_ok=True)
    new_file = not os.path.exists(ENTRY_SIGNALS_PATH)
    with open(ENTRY_SIGNALS_PATH, "a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=ENTRY_SIGNALS_FIELDS)
        if new_file:
            w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in ENTRY_SIGNALS_FIELDS})


# live screener.in fetch politeness (see build_candidate): matches the batch
# fetcher's 1.8s pause; budget bounds a freak all-alerts night
_LIVE_FETCH_PAUSE_S = 1.8
_LIVE_FETCH_BUDGET = 15
_LIVE_FETCHES = {"n": 0}


def entry_status_of(tag_result: dict) -> str:
    """Human label for how faithfully an alert matches the backtested trigger."""
    if tag_result.get("validated_entry"):
        return "VALIDATED"          # fresh volume breakout over VCP pivot
    if tag_result.get("vcp_valid"):
        return "AWAITING TRIGGER"   # VCP base live, pivot not yet cleared on volume
    return "NO VCP BASE"            # trend-following read only


def build_candidate(sym: str, tag_result: dict, industry: str | None,
                    rs_pctile: float | None, company_name: str = "") -> dict:
    """Conviction card + journal fields for an alerted name. Fundamentals and
    news are CONTEXT for the human (and vetoes) — never a machine gate
    (matrix v1/v2, brief section 2B). Phase C enrichment runs here, on the
    1-3 alerted names only."""
    raw = load_company(sym)
    # cloud-coverage fix (2026-07-18): the cache is only pre-filled for the
    # weekly CONFIRMED/ANTICIPATION shortlist, so re-entry/extended alerts
    # scored fundamentals-blind (coverage 45%, five dims "no info"). Fetch
    # live when missing/stale, never fatal. Politeness guards (audit
    # 2026-07-18): volatile nights can fire 15-25 buy-type alerts (Jul-14
    # had 23), so pause between live fetches and cap the per-night budget —
    # names over budget just score technical-only tonight and heal at the
    # next weekly refresh.
    if raw is None or _age_days(raw) > 7.0:
        why = "absent" if raw is None else "stale"
        if _LIVE_FETCHES["n"] >= _LIVE_FETCH_BUDGET:
            print(f"  fundamentals fetch budget ({_LIVE_FETCH_BUDGET}/night) "
                  f"exhausted — {sym} scores technical-only tonight", flush=True)
        else:
            try:
                if _LIVE_FETCHES["n"]:
                    time.sleep(_LIVE_FETCH_PAUSE_S)
                _LIVE_FETCHES["n"] += 1
                raw = fetch_company(sym)
                save_company(sym, raw)
                print(f"  fundamentals fetched live for {sym} (cache was {why})",
                      flush=True)
            except Exception as e:  # noqa: BLE001 — screener.in down != scan down
                print(f"  fundamentals fetch failed for {sym}: {str(e)[:80]}",
                      flush=True)
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
    risk_scale = market_risk_scale()
    plan = compute_entry_plan(tag_result["last_close"], atr=atr,
                              risk_scale=risk_scale) if atr else {}

    # structured detail blob for the dashboard drawer — SAME schema as
    # run_shortlist's shortlist_details.json, so every alerted name gets the
    # full why-this-score/plan/news drawer, not just the weekly shortlist 84
    # (the "empty drawer on alerted stocks" gap, user-caught 2026-07-10)
    plan_trim = {}
    if plan and not plan.get("skip"):
        keys = ("entry_price", "stop_loss_price", "risk_per_share", "shares_total",
                "shares_trading_lot", "shares_core_lot", "position_value",
                "capital_at_risk", "risk_scale")
        plan_trim = {k: plan[k] for k in keys if k in plan}
        plan_trim["breakeven_trigger"] = plan.get("breakeven_move_trigger_price")
        plan_trim["partial_price"] = plan.get("partial_profit_price")
    news_blob = None
    if news.get("ok"):
        news_blob = {
            "count": news["headline_count"], "trusted": news.get("trusted_count", 0),
            "sentiment": news.get("sentiment", 0.0),
            "sent_pos": news.get("sent_pos", 0), "sent_neg": news.get("sent_neg", 0),
            "themes": news["themes"], "events": news["events"],
            "red_flags": news["red_flags"],
            "filings": [{"d": str(f.get("date", ""))[:10], "t": f["subject"][:110]}
                        for f in news.get("filings", [])[:3]],
            "headlines": [{"d": h["date"].strftime("%d %b"), "t": h["text"][:110],
                           "s": h["source"], "tr": h.get("trusted", False),
                           "ru": h.get("roundup", False),
                           "sn": h.get("sentiment", 0)}
                          for h in news.get("headlines", [])[:5]],
        }
    detail = {
        "alerted_at": datetime.now().strftime("%Y-%m-%d"),
        "score": conviction.score, "coverage": conviction.coverage_pct,
        "label": conviction.label,
        "reasons": tag_result.get("reasons", []),
        "stage_name": tag_result.get("stage", {}).get("stage_name", ""),
        "tt_checks": tag_result.get("trend_template_checks_passed", 0),
        "vcp": tag_result.get("vcp_valid", False),
        "dims": [{"k": d["key"], "w": d["weight"], "s": d["score"],
                  "live": d["live"], "n": str(d["notes"])[:220]}
                 for d in conviction.per_dimension],
        "veto_reasons": conviction.veto_reasons,
        "plan": plan_trim,
        "news": news_blob,
    }

    return {
        "card": render_card(sym, tag_result, conviction, atr=atr,
                            archetypes=archetypes, dim_notes=True, news=news,
                            risk_scale=risk_scale),
        "detail": detail,
        "close": tag_result["last_close"],
        "atr": round(atr, 2) if atr else "",
        "stop_suggested": plan.get("stop_loss_price", ""),
        "conviction_score": conviction.score,
        "coverage_pct": conviction.coverage_pct,
        "vetoed": conviction.vetoed,
        "veto_reasons": "; ".join(conviction.veto_reasons),
        "archetypes": " + ".join(archetypes) if archetypes else "",
    }


def save_alert_details(new: dict) -> None:
    """Merge alert-time drawer details into state/alert_details.json.
    Entries expire after 30 days (the drawer only needs recent alerts;
    the weekly shortlist file covers the standing names)."""
    if not new:
        return
    path = os.path.join(ROOT, "state", "alert_details.json")
    data = {}
    if os.path.exists(path):
        try:
            data = json.load(open(path, encoding="utf-8"))
        except ValueError:
            data = {}
    cutoff = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    data = {s: d for s, d in data.items() if str(d.get("alerted_at", "")) >= cutoff}
    data.update(new)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, default=str)


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

    # persist today's NSE filings into our archive (the live feed forgets)
    feed_problems: list[str] = []
    try:
        from data.announcements_fetch import archive_feed
        n_new = archive_feed()
        print(f"filings archive: +{n_new} new NSE announcements", flush=True)
    except Exception as e:  # noqa: BLE001
        feed_problems.append(f"NSE announcements feed unreachable ({str(e)[:60]})")

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

    # FRESH nightly RS percentile across tonight's whole watched universe —
    # the weekly focus_list.csv percentile is up to 6 days stale, and it feeds
    # the 20-weight technical dimension. Rank the live rs_blend so the card's
    # RS reflects today, not the last weekend (audit fix 2026-07-12).
    rs_blends = {s: tr.get("rs", {}).get("rs_blend")
                 for s, tr in tag_results.items()
                 if tr.get("rs", {}).get("rs_blend") is not None}
    if rs_blends:
        rs_live = (pd.Series(rs_blends).rank(pct=True) * 100).round(1)
        rs_by_sym = {**rs_by_sym, **rs_live.to_dict()}  # live wins; keep any focus-only names

    prev = load_state(args.state_file)
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [f"# Daily scan — {now}", ""]
    cards: list[str] = []
    journal_rows: list[dict] = []
    entry_signal_rows: list[dict] = []
    alert_details: dict[str, dict] = {}

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
                tr = tag_results[sym]
                row = {"logged_at": now, "symbol": sym, "kind": kind,
                       "old_tag": old, "new_tag": new,
                       "rs_pctile": rs_by_sym.get(sym, "")}
                if kind in ("BUY CANDIDATE", "RE-ENTRY WINDOW"):
                    status = entry_status_of(tr)
                    lines.append(f"- **{kind}** [{status}]: {sym}  ({old} -> {new})")
                    entry_signal_rows.append({
                        "logged_at": now, "symbol": sym, "kind": kind,
                        "entry_status": status,
                        "validated_entry": tr.get("validated_entry"),
                        "close": tr["last_close"], "pivot_price": tr.get("pivot_price"),
                        "breakout_today": tr.get("breakout_today"),
                        "breakout_volume_ratio": tr.get("breakout_volume_ratio"),
                        "vcp_valid": tr.get("vcp_valid"),
                    })
                    cand = build_candidate(sym, tr,
                                           industry_by_sym.get(sym), rs_by_sym.get(sym),
                                           company_name=company_by_sym.get(sym, sym))
                    cards.append(cand.pop("card"))
                    alert_details[sym] = cand.pop("detail")
                    row.update(cand)
                else:
                    lines.append(f"- **{kind}**: {sym}  ({old} -> {new})")
                    row["close"] = tr["last_close"]
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
    try:
        feed_problems += [f"position drift: {p}" for p in sync_check()]
    except Exception:  # noqa: BLE001
        pass
    # per-holding staleness: a renamed/suspended symbol freezes silently while
    # the rest of the universe updates fine — the aggregate <80% check can't
    # catch one frozen name you actually OWN (audit fix 2026-07-12)
    for h in sorted(holdings):
        hdf = load_ohlcv(h)
        if hdf is None or hdf.empty:
            feed_problems.append(f"HELD {h}: no price data cached — symbol renamed/suspended?")
        else:
            age = (datetime.now() - hdf["date"].iloc[-1]).days
            if age > 5:
                feed_problems.append(f"HELD {h}: price {age}d stale — likely renamed/suspended, "
                                     "check the Yahoo ticker")
    # AI analyst heartbeat: a persistent auth/session failure silently starves
    # the verdicts + paper book; surface the last run's status loudly
    ah_path = os.path.join(ROOT, "state", "analyst_health.json")
    if os.path.exists(ah_path):
        try:
            ah = json.load(open(ah_path, encoding="utf-8"))
            if ah.get("status") == "failed":
                feed_problems.append(f"AI analyst last run FAILED ({ah.get('note', '')[:70]}) "
                                     "— verdicts missing, review cards manually")
        except (ValueError, KeyError):
            pass
    problems = health_check(today_tags, symbols, extra_problems=feed_problems)
    if problems:
        lines = lines[:2] + problems + [""] + lines[2:]

    save_state(args.state_file, today_tags)
    journal_append(journal_rows)
    entry_signals_append(entry_signal_rows)
    save_alert_details(alert_details)

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
