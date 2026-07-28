"""
scripts/daily_scan.py — the daily post-close job (pipeline steps 4-6), now
EVIDENCE-ALIGNED (2026-07-06): watches the FULL universe + holdings, because
the validated system entered breakouts from the whole universe — restricting
the scan to the focus list would silently add a gate no backtest ever tested.
The focus list remains a reporting/prioritization convenience only.

  1. incremental price update (whole universe + holdings + benchmark)
  2. re-tag every watched name (mechanical stage tags)
  3a. DIFF vs saved state -> transitions:
        * -> CONFIRMED                BUY CANDIDATE (conviction card attached)
        EXTENDED -> CONFIRMED         RE-ENTRY WINDOW (card attached)
        * -> ANTICIPATION             WATCH CLOSELY (zero capital)
        holding -> BROKEN             EXIT WARNING
  3b. EVENTS (not transitions — fire on any watched name, idempotent by bar):
        VCP pivot cleared on volume   BUY TRIGGER  <- the backtested entry
        gap >=8% on >=3x volume       EPISODIC PIVOT
      Transitions alone were missing ~73% of validated entries; see
      AUDIT_2026-07-25.md Finding 1.
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

from config import NEWS
from data.cache import load_ohlcv
from data.screener_fetch import fetch_company, load_company, save_company
from scoring.conviction import assess
from scoring.phase_b import build_dimensions, build_vetoes, tag_archetypes
from scoring.phase_c import enrich, enrichment_dimensions
from scoring.stage_tagger import tag_stock
from scoring.technical_score import (compute_atr, compute_entry_plan,
                                     detect_episodic_pivot)
from reports.watchlist_card import render_card
from scoring.regime import market_risk_scale, save_breadth_snapshot
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
# news_primed / news_pressure appended 2026-07-26: the news layer's own ruler.
# Frozen here at alert time and never recomputed, so "did NEWS-PRIMED alerts
# outperform?" becomes a measurable cohort — the same discipline that made
# entry_status auditable without ever gating on it. A cohort you can rewrite
# proves nothing, which is why these live in the record and not in the
# derived state file.
ENTRY_SIGNALS_FIELDS = ["logged_at", "symbol", "kind", "entry_status",
                        "validated_entry", "close", "pivot_price",
                        "breakout_today", "breakout_volume_ratio", "vcp_valid",
                        "news_primed", "news_pressure", "news_stories",
                        # the 2026-07-28 reading layer, frozen the same way and
                        # for the same reason: "did alerts carrying a real,
                        # sized catalyst outperform ones that did not?" is only
                        # answerable if the read is recorded at alert time. The
                        # engine will keep improving; a cohort recomputed by a
                        # later engine measures the engine, not the signal.
                        "news_catalyst", "news_lead_event", "news_scoreable"]

# A name that keeps closing over its pivot on volume would otherwise alert
# several nights running. One BUY TRIGGER per name per this many days; matches
# the state-retention window in save_state.
BUY_TRIGGER_COOLDOWN_DAYS = 10

# Analyst heartbeat thresholds. A quiet stretch with no buy alerts is a
# legitimate idle, so these sit above normal quiet — but well under the week
# that both the 07-21 analyst outage and the committee outage went unnoticed.
ANALYST_SILENT_DAYS = 3       # the job has not run at all
ANALYST_NO_SUCCESS_DAYS = 7   # it runs, but has produced nothing


def health_check(today_tags: dict, symbols: list[str],
                 extra_problems: list[str] | None = None,
                 last_bars: dict | None = None) -> list[str]:
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
    # UNIVERSE-WIDE staleness. Every check above passes when the whole universe
    # is uniformly one session behind: the benchmark is one of the ~20% that did
    # refresh, every name still tags, and no single holding looks odd. That is
    # exactly the 2026-07-24 failure — 646 names a session stale, reported as a
    # normal night. Compare each name to the NEWEST bar anywhere in the cache
    # (self-referential on purpose: no trading calendar needed, and a market
    # holiday moves every symbol together so it cannot false-positive).
    lasts = last_bars or {}
    if lasts:
        newest = max(lasts.values())
        behind = [s for s, d in lasts.items() if d < newest]
        frac = len(behind) / len(lasts)
        if frac > 0.10:
            problems.append(
                f"{len(behind)} of {len(lasts)} names ({frac:.0%}) are behind the "
                f"newest cached bar ({newest.date()}) — the price refresh did not "
                f"complete; those tags are computed on stale closes")
    if today_tags:
        counts = pd.Series(list(today_tags.values())).value_counts()
        if counts.index[0] == "WATCH" and counts.iloc[0] > 0.95 * len(today_tags):
            problems.append("tagger degenerate: >95% WATCH — indicator inputs look broken")
    # Screener parser health, written by the weekly fundamentals job.
    #
    # This block used to be `if os.path.exists(...)` with no else, and
    # state/parser_health.json is gitignored and was committed by no workflow
    # and cached by nothing — so in the cloud the file never existed, and BOTH
    # alarms below (parser degraded, weekly job dead) were unreachable in the
    # only environment that runs unattended. A health check that cannot fire
    # is indistinguishable from a healthy system, which is the failure mode
    # this whole function exists to prevent. The file is now committed by
    # weekly.yml, and its ABSENCE is itself reported.
    ph_path = os.path.join(ROOT, "state", "parser_health.json")
    if not os.path.exists(ph_path):
        problems.append(
            "no state/parser_health.json — the weekly fundamentals job has "
            "never reported in, so the parser-degraded and stale-fundamentals "
            "alarms are both blind")
    else:
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
        except (ValueError, KeyError) as e:
            # a corrupt file is a failure too, not a reason to fall silent
            problems.append(f"state/parser_health.json unreadable ({type(e).__name__}) "
                            "— parser health is unknown, not good")
    return [f"!! HEALTH: {p}" for p in problems]


def load_state(path: str) -> dict | None:
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def save_state(path: str, tags: dict, ep_alerted: dict | None = None,
               entry_alerted: dict | None = None) -> None:
    if _skip_write(f"state -> {os.path.basename(path)} (+ history snapshot)"):
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    payload = {"date": datetime.now().strftime("%Y-%m-%d"), "tags": tags}
    cutoff = (datetime.now() - pd.Timedelta(days=10)).strftime("%Y-%m-%d")
    if ep_alerted:
        # EP alerts are one-day EVENTS, not state transitions — remember which
        # (symbol, bar-date) pairs already fired so a same-evening catch-up
        # re-run can't journal the same event twice. Keep 10 days.
        payload["ep_alerted"] = {s: d for s, d in ep_alerted.items() if d >= cutoff}
    if entry_alerted:
        # BUY TRIGGER alerts are events too, on exactly the same terms.
        payload["entry_alerted"] = {s: d for s, d in entry_alerted.items()
                                    if d >= cutoff}
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


# Set by --dry-run. Every persistent write in this file checks it, so the whole
# nightly path can be exercised against real data without touching the
# append-only record. The 2026-07-09 intraday incident and the 2026-07-07
# synthetic row both entered the journal through a TEST run that had no way to
# say "compute everything, write nothing"; this is that way.
DRY_RUN = False


def _skip_write(what: str) -> bool:
    if DRY_RUN:
        print(f"  [dry-run] would write {what}", flush=True)
        return True
    return False


def journal_append(rows: list[dict]) -> None:
    if not rows:
        return
    if _skip_write(f"{len(rows)} row(s) -> {os.path.basename(JOURNAL_PATH)}"):
        return
    os.makedirs(os.path.dirname(JOURNAL_PATH), exist_ok=True)
    new_file = not os.path.exists(JOURNAL_PATH)
    with open(JOURNAL_PATH, "a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=JOURNAL_FIELDS)
        if new_file:
            w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in JOURNAL_FIELDS})


def _widen_entry_signals_header() -> None:
    """One-time, value-preserving widening when new columns are added.

    Appending 13-field rows under a 10-field header silently shifts every new
    value into the wrong column, which would corrupt the one file that has to
    stay trustworthy. So: if the header is a strict PREFIX of the current
    schema, rewrite it with the new columns left blank on historic rows (they
    genuinely had no news read) and say so out loud. Anything other than a
    clean prefix is a real divergence — refuse and let a human look."""
    if not os.path.exists(ENTRY_SIGNALS_PATH):
        return
    with open(ENTRY_SIGNALS_PATH, encoding="utf-8", newline="") as f:
        rows = list(csv.reader(f))
    if not rows:
        return
    head = rows[0]
    if head == ENTRY_SIGNALS_FIELDS:
        return
    if head != ENTRY_SIGNALS_FIELDS[:len(head)]:
        raise RuntimeError(
            f"entry_signals.csv header diverges from the schema: {head}")
    pad = [""] * (len(ENTRY_SIGNALS_FIELDS) - len(head))
    with open(ENTRY_SIGNALS_PATH, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(ENTRY_SIGNALS_FIELDS)
        for r in rows[1:]:
            w.writerow(r + pad)
    print(f"entry_signals.csv widened by {len(pad)} column(s); "
          f"{len(rows) - 1} historic rows preserved, new fields blank",
          flush=True)


def entry_signals_append(rows: list[dict]) -> None:
    """Append entry-fidelity rows (buy/re-entry alerts only). Additive file."""
    if not rows:
        return
    if _skip_write(f"{len(rows)} row(s) -> {os.path.basename(ENTRY_SIGNALS_PATH)}"):
        return
    os.makedirs(os.path.dirname(ENTRY_SIGNALS_PATH), exist_ok=True)
    _widen_entry_signals_header()
    new_file = not os.path.exists(ENTRY_SIGNALS_PATH)
    with open(ENTRY_SIGNALS_PATH, "a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=ENTRY_SIGNALS_FIELDS)
        if new_file:
            w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in ENTRY_SIGNALS_FIELDS})


# Rolling news memory, loaded once per scan and shared by the card builder and
# the record stamper. ONE accessor rather than a lookup at each call site: this
# file already learned that lesson twice (BUY_ALERT_KINDS exists because four
# private copies of "is this a buy alert?" drifted apart in production).
_NEWS_READS: dict = {}


def news_pressure_for(sym: str):
    """PressureRead for a symbol, or None if the memory is unavailable. Never
    raises — no news memory must degrade to exactly the pre-2026-07-26
    behaviour, which was no news memory at all."""
    global _NEWS_READS
    if not _NEWS_READS:
        try:
            from data.news_pressure import load as load_pressure
            _NEWS_READS = load_pressure() or {"__empty__": True}
        except Exception:  # noqa: BLE001
            _NEWS_READS = {"__empty__": True}
    return _NEWS_READS.get(sym)


# What the reading layer said about each name enriched tonight, so the single
# stamping point below can freeze it without re-fetching. Populated by
# build_candidate; empty for names that were never enriched.
_NEWS_READ: dict[str, dict] = {}
# Names whose enrichment found EVERY source down. Blank columns get frozen for
# these rather than a zero, because "we could not look" and "we looked and
# found nothing" must not become the same row in the forward record.
_NEWS_BLIND: list[str] = []
# politeness between per-company Google News queries (matches the screener
# fetcher's pacing in spirit; a busy night enriches ~10 names)
_NEWS_FETCH_PAUSE_S = 0.6


def stamp_news_pressure(rows: list[dict]) -> None:
    """Freeze each alert's news read into the forward record, in place.

    Applied to EVERY entry-signal row from one place, so a new alert class
    cannot quietly ship without its news label the way EPISODIC PIVOT once
    shipped without paper-trader support."""
    for r in rows:
        sym = r.get("symbol", "")
        p = news_pressure_for(sym)
        r["news_primed"] = bool(p.primed) if p else False
        r["news_pressure"] = round(p.pressure, 3) if p else 0.0
        r["news_stories"] = p.n_pos if p else 0
        read = _NEWS_READ.get(sym) or {}
        r["news_catalyst"] = read.get("catalyst", "")
        r["news_lead_event"] = read.get("lead_event", "")
        r["news_scoreable"] = read.get("scoreable", "")
        # blank, not 0.0 — see _NEWS_BLIND. A zero here would enter the cohort
        # as "no catalyst" and quietly bias the very question the columns exist
        # to answer.
        if sym in _NEWS_BLIND:
            r["news_catalyst"] = r["news_lead_event"] = r["news_scoreable"] = ""


# live screener.in fetch politeness (see build_candidate): matches the batch
# fetcher's 1.8s pause; budget bounds a freak all-alerts night
_LIVE_FETCH_PAUSE_S = 1.8
_LIVE_FETCH_BUDGET = 15
_LIVE_FETCHES = {"n": 0}


def entry_status_of(tag_result: dict) -> str:
    """Human label for how faithfully an alert matches the backtested trigger."""
    if tag_result.get("validated_entry"):
        return "VALIDATED"          # fresh volume breakout over VCP pivot
    if tag_result.get("engine_entry"):
        # the engine's condition fired but the tag refuses to call it a buy —
        # almost always because the name is EXTENDED above its 50-DMA. The
        # backtest took these; live skips them. Label, don't hide (F1b).
        return "VALIDATED (EXTENDED)"
    if tag_result.get("vcp_valid"):
        return "AWAITING TRIGGER"   # VCP base live, pivot not yet cleared on volume
    return "NO VCP BASE"            # trend-following read only


def build_candidate(sym: str, tag_result: dict, industry: str | None,
                    rs_pctile: float | None, company_name: str = "",
                    ep: dict | None = None) -> dict:
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

    news = enrich(sym, company_name or sym, industry or "")
    if news.get("ok"):
        _top = news.get("top_story") or {}
        _NEWS_READ[sym] = {"catalyst": news.get("catalyst_score", 0.0),
                           "lead_event": _top.get("event", ""),
                           "scoreable": news.get("scoreable_count", 0)}
    elif news.get("blind"):
        # a news OUTAGE, not a quiet name — record it so the frozen cohort
        # never counts this alert as "had no catalyst"
        _NEWS_BLIND.append(sym)
        _NEWS_READ[sym] = {"catalyst": "", "lead_event": "", "scoreable": ""}
    # Google News is one host answering one query per alerted name. A busy
    # night can enrich a dozen; space them the way the fundamentals fetcher
    # does rather than burst.
    time.sleep(_NEWS_FETCH_PAUSE_S)
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
    # EPISODIC PIVOT alerts stop at the gap day's low, not 2.5xATR
    # (EP matrix, adopted 2026-07-19)
    plan = compute_entry_plan(tag_result["last_close"], atr=atr,
                              risk_scale=risk_scale,
                              stop_price=ep["stop_price"] if ep else None) \
        if atr else {}

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
            # phase_c already returns card-shaped headlines (old keys kept,
            # new judgements alongside) — pass them through rather than
            # rebuilding the shape in a second place and letting it drift
            "headlines": [{k: v for k, v in h.items()
                           if k in ("d", "t", "s", "tr", "ru", "sn", "rel",
                                    "kind", "tier", "ev", "nov", "amt")}
                          for h in news.get("headlines", [])[:8]],
            # the 2026-07-28 reading layer
            "scoreable": news.get("scoreable_count", 0),
            "stories": news.get("stories", 0),
            "top_story": news.get("top_story"),
            "dropped": news.get("dropped", {}),
            "theme_note": news.get("theme_note", ""),
        }
    detail = {
        "alerted_at": datetime.now().strftime("%Y-%m-%d"),
        "ep": ({"gap_pct": ep["gap_pct"], "vol_mult": ep["vol_mult"]}
               if ep else None),
        "score": conviction.score, "coverage": conviction.coverage_pct,
        "label": conviction.label,
        "reasons": tag_result.get("reasons", []),
        "stage_name": tag_result.get("stage", {}).get("stage_name", ""),
        "tt_checks": tag_result.get("trend_template_checks_passed", 0),
        "vcp": tag_result.get("vcp_valid", False),
        # VCP breakout pivot for the drawer chart geometry (display only);
        # kept in parity with run_shortlist's shortlist_details.json blob.
        "pivot_price": tag_result.get("pivot_price"),
        "dims": [{"k": d["key"], "w": d["weight"], "s": d["score"],
                  "live": d["live"], "n": str(d["notes"])[:220]}
                 for d in conviction.per_dimension],
        "veto_reasons": conviction.veto_reasons,
        "plan": plan_trim,
        "news": news_blob,
    }

    # NEWS MEMORY (2026-07-26): what has been building on this name BEFORE
    # tonight. Answers the standing question the single-window radar could not
    # ("has this been in the news a while?") at the only moment it matters —
    # when the technical trigger has actually fired. Context on the card and a
    # frozen label in the record; it changes no entry, stop or size.
    press = news_pressure_for(sym)
    if press is not None and (press.n_pos or press.n_neg):
        detail["news_pressure"] = {
            "p": press.pressure, "rp": press.risk_pressure,
            "n_pos": press.n_pos, "n_neg": press.n_neg,
            "primed": press.primed, "summary": press.summary(),
            "events": press.events[:6],
        }

    card_text = render_card(sym, tag_result, conviction, atr=atr,
                            archetypes=archetypes, dim_notes=True, news=news,
                            risk_scale=risk_scale)
    if press is not None and press.primed:
        card_text = (f"NEWS-PRIMED — {press.summary()}. The story was building "
                     f"before this trigger; unproven as an edge, tracked in the "
                     f"forward record.\n") + card_text
    elif press is not None and press.n_neg:
        card_text = (f"NEWS RISK — {press.n_neg} negative filing(s) in the last "
                     f"{NEWS.lookback_days}d. Read them before acting.\n") + card_text
    if ep:
        card_text = (f"!! EPISODIC PIVOT — gap +{ep['gap_pct']}% on "
                     f"{ep['vol_mult']}x volume ({ep['bar_date']}). Event stop "
                     f"= gap-day low {ep['stop_price']}. Check the news radar "
                     f"for the catalyst.\n") + card_text
    return {
        "card": card_text,
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
    if _skip_write(f"{len(new)} alert detail(s) -> state/alert_details.json"):
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
    parser.add_argument(
        "--dry-run", action="store_true",
        help="compute the whole scan and print it, but write NOTHING — no "
             "journal, no entry_signals, no state, no alerts file, no news "
             "archive. Implies --no-update. Use this to test the nightly path.")
    args = parser.parse_args()

    global DRY_RUN
    DRY_RUN = args.dry_run
    if DRY_RUN:
        args.no_update = True
        print("DRY RUN — no file will be written, prices will not be fetched\n",
              flush=True)

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
    feed_problems: list[str] = []
    if not args.no_update:
        print(f"updating prices for {len(symbols)} symbols...", flush=True)
        # The return value used to be discarded. On 2026-07-24 Yahoo rate-limited
        # the cloud runner after ~189 of 835 symbols; the other 646 failed, sat a
        # session stale, and the scan reported a normal night because nothing
        # read this list. Prices are the ONE input every tag, score and trigger
        # depends on — a failed refresh has to be as loud as a failed scan.
        ok, failures = update_symbols(symbols, pause=0.25)
        if failures:
            frac = len(failures) / max(1, len(symbols)) * 100
            head = ", ".join(failures[:5]) + ("..." if len(failures) > 5 else "")
            feed_problems.append(
                f"PRICE UPDATE FAILED for {len(failures)}/{len(symbols)} symbols "
                f"({frac:.0f}%) — tonight's tags are computed on STALE prices "
                f"for those names [{head}]")

    # persist today's NSE filings into our archive (the live feed forgets)
    if DRY_RUN:
        print("  [dry-run] skipping the NSE filings archive fetch", flush=True)
    else:
        try:
            from data.announcements_fetch import archive_feed
            n_new = archive_feed()
            print(f"filings archive: +{n_new} new NSE announcements", flush=True)
        except Exception as e:  # noqa: BLE001
            feed_problems.append(f"NSE announcements feed unreachable ({str(e)[:60]})")

    # Tier-1 journalism sweep (2026-07-28). Ten market-section RSS feeds
    # fetched ONCE and archived, then matched per company — the same shape as
    # the filings archive above, and the reason is the same: 651 per-company
    # queries would be absurd, one firehose is not. This is what stopped the
    # news mix being half auto-generated aggregator pages; coverage is
    # cumulative, so a fresh clone starts thin and fills in nightly.
    if DRY_RUN:
        print("  [dry-run] skipping the market news sweep", flush=True)
    else:
        try:
            from data.news_sources import sweep_market_feeds
            _sweep = sweep_market_feeds()
            if _sweep["all_failed"]:
                # not "fewer headlines tonight" — the tier-1 channel is DOWN,
                # and every card built after this is running on Google alone
                feed_problems.append(
                    "ALL market news feeds unreachable — tier-1 coverage is "
                    f"dark tonight ({'; '.join(_sweep['failed'][:3])})")
            elif _sweep["failed"] or _sweep["skipped"] or _sweep.get("stale"):
                bits = []
                if _sweep["failed"]:
                    bits.append(f"{len(_sweep['failed'])} unreachable")
                if _sweep["skipped"]:
                    bits.append(f"{len(_sweep['skipped'])} skipped on time budget")
                if _sweep.get("stale"):
                    # answering, parsing, and serving nothing current — the
                    # Moneycontrol failure mode, invisible to a success check
                    bits.append(f"{len(_sweep['stale'])} ABANDONED "
                                f"({'; '.join(_sweep['stale'][:3])})")
                feed_problems.append(
                    f"market news feeds: {', '.join(bits)} "
                    f"({_sweep['feeds_ok']}/{_sweep['feeds_total']} live)")
        except Exception as e:  # noqa: BLE001 — context must never kill the scan
            feed_problems.append(f"market news sweep failed ({str(e)[:60]})")

    # rolling news memory over that archive (2026-07-26). Derived and fully
    # rebuildable — the archive is the source of truth. Feeds card context and
    # the radar's "building" section; gates nothing.
    try:
        from data.news_pressure import scan as scan_news_pressure
        _np = scan_news_pressure(persist=not DRY_RUN)
        print(f"news memory: {len(_np)} symbols, "
              f"{sum(1 for r in _np.values() if r.primed)} primed", flush=True)
    except Exception as e:  # noqa: BLE001 — context must never kill the scan
        feed_problems.append(f"news memory failed ({str(e)[:60]})")

    bench = load_ohlcv("NIFTY50")
    today_tags: dict[str, str] = {}
    tag_results: dict[str, dict] = {}
    ep_hits: dict[str, dict] = {}
    last_bars: dict[str, pd.Timestamp] = {}
    breadth_above = breadth_total = 0
    for sym in symbols:
        if sym == "NIFTY50":
            continue
        df = load_ohlcv(sym)
        if df is None or len(df) < 60:
            continue
        # recorded here rather than re-read in health_check: this loop already
        # holds every frame, and the staleness check must not cost 600 re-reads
        last_bars[sym] = pd.Timestamp(df["date"].iloc[-1]).normalize()
        # EPISODIC PIVOT (adopted 2026-07-19): event check on tonight's bar.
        # Needs only 60 bars — young IPOs that can't form 45-week structures
        # (the IREDA blind spot) are exactly the point of this class.
        # Per-symbol guard: one pathological CSV must never kill the scan.
        try:
            ep = detect_episodic_pivot(df)
            if ep:
                ep_hits[sym] = ep
            # market breadth for the regime rule (sizing matrix v3+v3b,
            # adopted 2026-07-19): % of universe above its own 200-DMA.
            # Computed here because this loop already holds every chart.
            if len(df) >= 200:
                breadth_total += 1
                if float(df["close"].iloc[-1]) > float(df["close"].tail(200).mean()):
                    breadth_above += 1
        except Exception as e:  # noqa: BLE001
            print(f"  ep/breadth check failed for {sym}: {str(e)[:60]}", flush=True)
        if len(df) < 260:
            continue
        t = tag_stock(df, bench)
        today_tags[sym] = t["tag"]
        tag_results[sym] = t
    # persist BEFORE any market_risk_scale() call so tonight's alerts and
    # plans size off tonight's breadth (regime.py reads this snapshot).
    # Never fatal — on failure regime.py falls back to the NIFTY/150 rule.
    try:
        if DRY_RUN:
            pct = round(breadth_above / breadth_total * 100, 1) if breadth_total else 0
            print(f"  [dry-run] would write state/regime.json — breadth {pct}% "
                  f"of {breadth_total}; regime reads the LAST saved snapshot",
                  flush=True)
        else:
            snap = save_breadth_snapshot(breadth_above, breadth_total)
            print(f"breadth: {snap['breadth_pct_above_200dma']}% of {breadth_total} "
                  f"above their 200-DMA -> risk x{market_risk_scale()}", flush=True)
    except Exception as e:  # noqa: BLE001
        feed_problems.append(f"breadth snapshot failed ({str(e)[:60]}) — "
                             "regime fell back to NIFTY/150 rule")

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
    card_idx: dict[str, int] = {}   # sym -> index into cards (same-night dedupe)
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
                    card_idx[sym] = len(cards) - 1
                    alert_details[sym] = cand.pop("detail")
                    row.update(cand)
                else:
                    lines.append(f"- **{kind}**: {sym}  ({old} -> {new})")
                    row["close"] = tr["last_close"]
                journal_rows.append(row)
        if infos:
            lines.append("")
            lines.append("Minor shifts: " + ", ".join(f"{s} {o}->{n}" for s, o, n in infos))

    # BUY TRIGGER alerts (AUDIT_2026-07-25 Finding 1, ADOPTED 2026-07-25).
    #
    # The entry the +1.67R evidence is actually built on — a VCP pivot cleared
    # on volume inside a passing trend template — was already computed for
    # EVERY watched name every night by tag_stock, and then thrown away for all
    # but the handful that happened to change tag. Measured on a 60-stock /
    # 6.2-year sample: the engine's entry fires 66 times, the live tagger
    # agrees on 55, but only 15 of those 55 land on a tag-TRANSITION day — so
    # ~73% of validated entries could never produce an alert. Live
    # corroboration: 117 buy-type alerts through 2026-07-24, ZERO ever
    # labelled VALIDATED.
    #
    # This fires it as an EVENT, mirroring EPISODIC PIVOT. No new signal, no
    # new gate, no threshold moved, nothing recomputed — an already-validated
    # entry simply becomes alertable. Expected ~1.7/week across 611 names.
    entry_alerted: dict[str, str] = dict((prev or {}).get("entry_alerted", {}))
    if prev is not None:
        # names that already got a buy-type card tonight (a transition that was
        # ITSELF the validated entry) — record the event so it can't re-fire
        # tomorrow, but don't build a second alert for the same thing
        already_carded = set(card_idx)
        entry_hits = {s: tr for s, tr in tag_results.items()
                      if tr.get("validated_entry") or tr.get("engine_entry")}
        new_entries = {}
        for sym, tr in entry_hits.items():
            bar = tr.get("last_date", "")
            # idempotent on the bar (a same-evening catch-up re-run must not
            # double-journal), plus a cooldown so a name that keeps closing
            # over its pivot on volume doesn't alert three nights running.
            # 10 days matches the state-retention window in save_state.
            last = entry_alerted.get(sym)
            if last and (pd.Timestamp(bar) - pd.Timestamp(last)).days < BUY_TRIGGER_COOLDOWN_DAYS:
                continue
            entry_alerted[sym] = bar
            if sym not in already_carded:
                new_entries[sym] = tr
        if new_entries:
            lines.append("")
            lines.append(f"{len(new_entries)} BUY TRIGGER(s) — the backtested "
                         f"entry fired (VCP pivot cleared on volume):")
            lines.append("")
        # strongest first: a validated entry on the biggest volume expansion
        for sym, tr in sorted(new_entries.items(),
                              key=lambda kv: -(kv[1].get("breakout_volume_ratio") or 0)):
            status = entry_status_of(tr)
            volx = tr.get("breakout_volume_ratio")
            vol_txt = f"{volx:.1f}x vol" if volx else "volume confirmed"
            # ONE trailing parenthesised group — send_telegram's ALERT_RX
            # parses these lines, so keep the shape identical to every other
            # alert line rather than appending a second group
            detail = f"pivot {tr.get('pivot_price')} cleared on {vol_txt}"
            if status == "VALIDATED (EXTENDED)":
                detail += ("; tagger says EXTENDED — the backtest TOOK these, "
                           "live has been skipping them")
            lines.append(f"- **BUY TRIGGER** [{status}]: {sym}  ({detail})")
            entry_signal_rows.append({
                "logged_at": now, "symbol": sym, "kind": "BUY TRIGGER",
                "entry_status": status,
                "validated_entry": tr.get("validated_entry"),
                "close": tr["last_close"], "pivot_price": tr.get("pivot_price"),
                "breakout_today": tr.get("breakout_today"),
                "breakout_volume_ratio": volx,
                "vcp_valid": tr.get("vcp_valid"),
            })
            row = {"logged_at": now, "symbol": sym, "kind": "BUY TRIGGER",
                   "old_tag": (prev.get("tags", {}) or {}).get(sym, ""),
                   "new_tag": today_tags.get(sym, ""),
                   "rs_pctile": rs_by_sym.get(sym, "")}
            cand = build_candidate(sym, tr, industry_by_sym.get(sym),
                                   rs_by_sym.get(sym),
                                   company_name=company_by_sym.get(sym, sym))
            banner = (f"!! BUY TRIGGER — pivot {tr.get('pivot_price')} cleared on "
                      f"{vol_txt} ({tr.get('last_date')}). This is the exact "
                      f"entry the backtest validated.\n")
            if status == "VALIDATED (EXTENDED)":
                banner += ("!! ...but the tag reads EXTENDED. The backtest took "
                           "these; the live system has been skipping them. "
                           "Labelled for measurement — not a recommendation.\n")
            cards.append(banner + cand.pop("card"))
            card_idx[sym] = len(cards) - 1
            alert_details[sym] = cand.pop("detail")
            row.update(cand)
            journal_rows.append(row)

    # EPISODIC PIVOT alerts (EP matrix, ADOPTED 2026-07-19): one-day EVENTS,
    # not state transitions — a violent gap on extreme volume. Idempotent via
    # state ep_alerted {sym: bar_date} (a same-evening catch-up re-run of the
    # same bar must not journal the event twice). Fires only once a baseline
    # exists (prev is not None), same convention as transition alerts.
    ep_alerted: dict[str, str] = dict((prev or {}).get("ep_alerted", {}))
    if prev is not None and ep_hits:
        new_eps = {s: e for s, e in ep_hits.items()
                   if ep_alerted.get(s) != e["bar_date"]}
        if new_eps:
            lines.append("")
            lines.append(f"{len(new_eps)} episodic pivot(s) — gap + volume event:")
            lines.append("")
        for sym, e in sorted(new_eps.items(),
                             key=lambda kv: -kv[1]["vol_mult"]):
            ep_alerted[sym] = e["bar_date"]
            tr = tag_results.get(sym)
            row = {"logged_at": now, "symbol": sym, "kind": "EPISODIC PIVOT",
                   "old_tag": (prev.get("tags", {}) or {}).get(sym, ""),
                   "new_tag": today_tags.get(sym, "YOUNG"),
                   "close": e["close"], "stop_suggested": e["stop_price"],
                   "rs_pctile": rs_by_sym.get(sym, "")}
            entry_signal_rows.append({
                "logged_at": now, "symbol": sym, "kind": "EPISODIC PIVOT",
                "entry_status": "EP EVENT", "validated_entry": True,
                "close": e["close"], "pivot_price": "",
                "breakout_today": True,
                "breakout_volume_ratio": e["vol_mult"], "vcp_valid": "",
            })
            if tr is not None:
                lines.append(f"- **EPISODIC PIVOT** [EP EVENT]: {sym}  "
                             f"(gap +{e['gap_pct']}% on {e['vol_mult']}x vol)")
                if sym in card_idx:
                    # same-night transition alert already built this card —
                    # don't rebuild (double card + double fetch); prepend the
                    # EP banner and note the event on the existing detail
                    banner = (f"!! EPISODIC PIVOT — gap +{e['gap_pct']}% on "
                              f"{e['vol_mult']}x volume ({e['bar_date']}). Event "
                              f"stop = gap-day low {e['stop_price']}. Check the "
                              f"news radar for the catalyst.\n")
                    cards[card_idx[sym]] = banner + cards[card_idx[sym]]
                    if sym in alert_details:
                        alert_details[sym]["ep"] = {"gap_pct": e["gap_pct"],
                                                    "vol_mult": e["vol_mult"]}
                else:
                    cand = build_candidate(sym, tr, industry_by_sym.get(sym),
                                           rs_by_sym.get(sym),
                                           company_name=company_by_sym.get(sym, sym),
                                           ep=e)
                    cards.append(cand.pop("card"))
                    card_idx[sym] = len(cards) - 1
                    alert_details[sym] = cand.pop("detail")
                    cand.pop("stop_suggested", None)  # keep the EP event stop
                    row.update(cand)
            else:
                # young stock (<260 bars — no stage read exists): compact
                # alert with the event plan; exactly the IPO blind spot the
                # EP class was adopted to cover
                plan = compute_entry_plan(e["close"],
                                          atr=None, risk_scale=market_risk_scale(),
                                          stop_price=e["stop_price"])
                stop_txt = (f"stop {e['stop_price']}" if not plan.get("skip")
                            else f"NO PLAN — {plan.get('skip_reason', '')[:60]}")
                lines.append(f"- **EPISODIC PIVOT** [EP EVENT]: {sym}  "
                             f"(gap +{e['gap_pct']}% on {e['vol_mult']}x vol, "
                             f"young listing, {stop_txt})")
            journal_rows.append(row)

    # news-first discovery radar (2026-07-19): material filings since the
    # last scan, classified + cross-referenced with tonight's technical
    # state. News moves ATTENTION, never entries — trades stay technical.
    try:
        from data.news_radar import radar_md_section, scan_radar
        radar = scan_radar(today_tags, rs_by_sym, holdings, persist=not DRY_RUN)
        lines += radar_md_section(radar)
        if radar.get("hits"):
            print(f"news radar: {len(radar['hits'])} material filing hit(s)",
                  flush=True)
    except Exception as e:  # noqa: BLE001 — discovery must never kill the scan
        feed_problems.append(f"news radar failed ({str(e)[:60]})")

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
    #
    # write_health() records last_success_at *specifically* so that "a run of
    # failures is visible as a growing gap, not just a single flag" — and this
    # reader only ever looked at status. A heartbeat that says ok and is three
    # weeks old read as healthy, which is exactly how the analyst went dead
    # 07-21 -> 07-25 and the committee went dead for a week, both noticed by
    # accident. Two different failures, so two different checks:
    #   checked_at stale      -> the job is not running at all
    #   last_success_at stale -> it runs and never succeeds
    ah_path = os.path.join(ROOT, "state", "analyst_health.json")
    if os.path.exists(ah_path):
        try:
            ah = json.load(open(ah_path, encoding="utf-8"))
            if ah.get("status") == "failed":
                feed_problems.append(f"AI analyst last run FAILED ({ah.get('note', '')[:70]}) "
                                     "— verdicts missing, review cards manually")
            for field, limit, msg in (
                    ("checked_at", ANALYST_SILENT_DAYS,
                     "AI analyst has not reported in for {n}d — the job itself "
                     "looks dead (scheduled task / workflow), not just its dives"),
                    ("last_success_at", ANALYST_NO_SUCCESS_DAYS,
                     "AI analyst has not produced a verdict in {n}d — it is "
                     "running but never succeeding")):
                stamp = ah.get(field)
                if not stamp:
                    continue
                age = (datetime.now() - datetime.strptime(stamp, "%Y-%m-%d %H:%M")).days
                if age > limit:
                    feed_problems.append(msg.format(n=age))
        except (ValueError, KeyError, TypeError):
            feed_problems.append("state/analyst_health.json unreadable — analyst "
                                 "status unknown, not good")
    problems = health_check(today_tags, symbols, extra_problems=feed_problems,
                            last_bars=last_bars)
    if problems:
        lines = lines[:2] + problems + [""] + lines[2:]

    save_state(args.state_file, today_tags, ep_alerted=ep_alerted,
               entry_alerted=entry_alerted)
    journal_append(journal_rows)
    if _NEWS_BLIND:
        # loud, because every card for these names says "news unavailable" and
        # a reader could otherwise take that for "nothing was happening"
        print(f"  !! news sources were unreachable for {len(_NEWS_BLIND)} alerted "
              f"name(s): {', '.join(_NEWS_BLIND[:6])}"
              f"{' +more' if len(_NEWS_BLIND) > 6 else ''} — their catalyst "
              f"columns are blank, not zero", flush=True)
    stamp_news_pressure(entry_signal_rows)
    entry_signals_append(entry_signal_rows)
    save_alert_details(alert_details)

    report = "\n".join(lines)
    if cards:
        report += "\n\n## Cards\n\n```\n" + "\n".join(cards) + "\n```\n"
    out_path = os.path.join(ROOT, "daily_alerts.md")
    if not _skip_write(os.path.basename(out_path)):
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(report)
    print(report)
    if DRY_RUN:
        print(f"\nDRY RUN complete — nothing written. Would have produced "
              f"{len(journal_rows)} journal row(s), "
              f"{len(entry_signal_rows)} entry-signal row(s), "
              f"{len(cards)} card(s).")
        return
    print(f"\n-> {out_path}")
    if journal_rows:
        print(f"-> {len(journal_rows)} row(s) appended to {JOURNAL_PATH}")


if __name__ == "__main__":
    main()
