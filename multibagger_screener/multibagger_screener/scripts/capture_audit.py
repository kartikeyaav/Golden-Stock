"""
scripts/capture_audit.py — Top-mover Capture-Recall audit.

THE QUESTION: "If this screener had been running over the last week / 1 / 3 /
6 months, would it have IDENTIFIED the stocks that actually moved the most —
and how early?"

This is a RECALL diagnostic, NOT the objective. The system optimizes
risk-adjusted expectancy (the matrix verdicts, VALIDATION_REPORT.md),
deliberately NOT recall. So every top mover is CLASSIFIED with a reason —
never reduced to a bare catch-rate that would tempt loosening entries (which
the evidence lock, PROJECT_BRIEF.md §2B, forbids). Only the MISSED bucket is
a genuine defect; the others are the system behaving as designed.

FAITHFULNESS: it reuses the LIVE decision logic as-of each historical date
with NO look-ahead — tag_stock() (CONFIRMED tag + validated VCP-breakout
entry) and detect_episodic_pivot() (the EP entry class adopted 2026-07-19) —
exactly what the nightly scan fires on. Same partial-bar-safe cache loader.

SCOPE: ranks movers WITHIN the 651-name watched universe (universe.csv), the
set the system actually scans. A stock outside that universe is reported as
NOT_IN_UNIVERSE only if named explicitly via --symbols; the top-N ranking is
by construction inside the universe. (A market-wide top-mover list would need
an external data pull — out of scope; noted as a limitation in the report.)

JOURNALED (so the weekly review can track recall over time, next to the
signal/outcome journals): appends one row per (audit_date, window, symbol) to
journal/capture_audit.csv. Also writes capture_audit_report.md (human) and
state/capture_audit.json (dashboard).

    python scripts/capture_audit.py                    # top-7, windows 1w,1m,3m,6m
    python scripts/capture_audit.py --windows 3m --top 7
    python scripts/capture_audit.py --symbols SUZLON BSE KPIGREEN --windows 3m
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

from config import UNIVERSE
from data.cache import load_ohlcv
from scoring.stage_tagger import tag_stock
from scoring.technical_score import detect_episodic_pivot

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UNIVERSE_CSV = os.path.join(PROJECT_ROOT, "universe.csv")
JOURNAL_CSV = os.path.join(PROJECT_ROOT, "journal", "capture_audit.csv")
REPORT_MD = os.path.join(PROJECT_ROOT, "capture_audit_report.md")
STATE_JSON = os.path.join(PROJECT_ROOT, "state", "capture_audit.json")

MIN_ROWS = 260          # tagger needs ~45 weeks + 200-DMA before it can classify
BENCH = "NIFTY50"

WINDOW_DAYS = {"1w": 7, "2w": 14, "1m": 30, "3m": 91, "6m": 182, "12m": 365}

# timeliness thresholds (fraction of the window's total peak-run still ahead
# at the moment we first flagged the stock as buyable)
EARLY_FRAC = 0.50
LATE_FRAC = 0.15

JOURNAL_FIELDS = [
    "audit_date", "window", "rank", "symbol", "window_return_pct",
    "turnover_cr", "classification", "identified", "signal_kind",
    "signal_date", "signal_px", "remaining_at_signal_pct",
    "total_peak_gain_pct", "timeliness", "validated_entry_date",
    "ep_date", "note",
]


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def load_universe() -> pd.DataFrame:
    return pd.read_csv(UNIVERSE_CSV)


def anchor_date() -> pd.Timestamp:
    """Latest completed bar available to the whole system (benchmark's last
    date). Everything is measured as-of this date so windows are consistent
    across names regardless of individual last-trade gaps."""
    b = load_ohlcv(BENCH)
    if b is None or b.empty:
        raise SystemExit("benchmark cache missing — cannot anchor windows")
    return pd.Timestamp(b["date"].iloc[-1])


def bar_on_or_before(df: pd.DataFrame, ts: pd.Timestamp):
    sub = df[df["date"] <= ts]
    return sub.iloc[-1] if len(sub) else None


def window_return(df: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp):
    """(return over window, end price, start price, avg turnover in Cr) or None
    when the stock wasn't trading at the window start (young listing)."""
    s = bar_on_or_before(df, start)
    e = bar_on_or_before(df, end)
    if s is None or e is None or float(s["close"]) <= 0:
        return None
    win = df[(df["date"] > start) & (df["date"] <= end)]
    if win.empty:
        return None
    turnover_cr = float((win["close"] * win["volume"]).mean()) / 1e7
    ret = float(e["close"]) / float(s["close"]) - 1
    return ret, float(e["close"]), float(s["close"]), turnover_cr


# --------------------------------------------------------------------------- #
# mover selection
# --------------------------------------------------------------------------- #
def select_movers(symbols: list[str], start: pd.Timestamp, end: pd.Timestamp,
                  top: int) -> tuple[list[dict], list[dict]]:
    """Rank universe symbols by window return, subject to the liquidity floor.
    Returns (top movers that were tradeable across the window, young-listing
    movers that IPO'd mid-window — surfaced separately so an IPO moonshot is
    never silently dropped, the IREDA/WAAREERTL lesson)."""
    scored, young = [], []
    for sym in symbols:
        df = load_ohlcv(sym)
        if df is None or df.empty:
            continue
        wr = window_return(df, start, end)
        if wr is None:
            # no bar at/*before* window start — did it list mid-window and run?
            first = pd.Timestamp(df["date"].iloc[0])
            e = bar_on_or_before(df, end)
            if first > start and e is not None and len(df) >= 30:
                first_px = float(df["close"].iloc[0])
                if first_px > 0:
                    young.append({
                        "symbol": sym,
                        "since_listing_pct": round((float(e["close"]) / first_px - 1) * 100, 1),
                        "listed": str(first.date()),
                    })
            continue
        ret, end_px, start_px, turnover_cr = wr
        if turnover_cr < UNIVERSE.min_avg_daily_turnover_cr:
            continue  # illiquid: circuit-to-circuit moves we can't actually trade
        if end_px < UNIVERSE.min_price:
            continue
        scored.append({
            "symbol": sym, "return_pct": round(ret * 100, 1),
            "end_px": round(end_px, 2), "start_px": round(start_px, 2),
            "turnover_cr": round(turnover_cr, 2),
        })
    scored.sort(key=lambda r: r["return_pct"], reverse=True)
    young.sort(key=lambda r: r["since_listing_pct"], reverse=True)
    return scored[:top], young[:top]


# --------------------------------------------------------------------------- #
# as-of walk + classification (the faithful core)
# --------------------------------------------------------------------------- #
def asof_timeline(df: pd.DataFrame, bench: pd.DataFrame,
                  start: pd.Timestamp, end: pd.Timestamp) -> tuple[list[dict], str | None]:
    """Re-run the live tagger + EP detector on every trading day in the window
    using ONLY data up to that day. Returns (per-day rows, prior_tag) where
    prior_tag is the tag as of the last bar BEFORE the window (so a stock that
    entered the window already CONFIRMED is distinguishable from a fresh
    transition)."""
    days = df[(df["date"] >= start) & (df["date"] <= end)]["date"].tolist()

    prior = df[df["date"] < start]
    prior_tag = None
    if len(prior) >= MIN_ROWS:
        try:
            b = bench[bench["date"] <= prior["date"].iloc[-1]] if bench is not None else None
            prior_tag = tag_stock(prior, b)["tag"]
        except Exception:  # noqa: BLE001
            prior_tag = None

    rows = []
    for t in days:
        sub = df[df["date"] <= t]
        if len(sub) < MIN_ROWS:
            # tagger can't run yet — but the EP class (needs only ~60 bars) can,
            # which is exactly the young-listing entry path
            ep = detect_episodic_pivot(sub) if len(sub) >= 65 else None
            rows.append({"date": t, "tag": "(young)", "validated_entry": False,
                         "ep": bool(ep), "close": float(sub["close"].iloc[-1])})
            continue
        b = bench[bench["date"] <= t] if bench is not None else None
        try:
            r = tag_stock(sub, b)
        except Exception:  # noqa: BLE001
            rows.append({"date": t, "tag": "(err)", "validated_entry": False,
                         "ep": False, "close": float(sub["close"].iloc[-1])})
            continue
        ep = detect_episodic_pivot(sub)
        rows.append({
            "date": t,
            "tag": r["tag"],
            "validated_entry": bool(r["validated_entry"]),
            "ep": bool(ep),
            "close": float(sub["close"].iloc[-1]),
        })
    return rows, prior_tag


def _peak_after(df: pd.DataFrame, signal_date: pd.Timestamp, end: pd.Timestamp) -> float:
    seg = df[(df["date"] >= signal_date) & (df["date"] <= end)]
    return float(seg["high"].max()) if len(seg) else float("nan")


def classify(df: pd.DataFrame, timeline: list[dict], prior_tag: str | None,
             start: pd.Timestamp, end: pd.Timestamp, start_px: float) -> dict:
    """Turn the as-of timeline into one honest label + the signal facts."""
    total_peak = _peak_after(df, start, end)
    total_peak_gain = (total_peak / start_px - 1) if start_px > 0 else float("nan")

    tags_seen = {r["tag"] for r in timeline}
    first_confirmed = next((r for r in timeline if r["tag"] == "CONFIRMED"), None)
    first_validated = next((r for r in timeline if r["validated_entry"]), None)
    first_ep = next((r for r in timeline if r["ep"]), None)
    first_antic = next((r for r in timeline if r["tag"] == "ANTICIPATION"), None)

    already = prior_tag == "CONFIRMED"

    # the moment the system first called this stock buyable (identification):
    # a validated entry / EP is the strict trigger; a CONFIRMED tag is the
    # radar-level identification. Take the EARLIEST of the identification
    # events as the "signal" for timeliness.
    candidates = [x for x in (first_confirmed, first_validated, first_ep) if x]
    signal = min(candidates, key=lambda r: r["date"]) if candidates else None

    kinds = []
    if first_validated:
        kinds.append("VALIDATED VCP ENTRY")
    if first_ep:
        kinds.append("EPISODIC PIVOT")
    if first_confirmed and not (first_validated or first_ep):
        kinds.append("CONFIRMED (watch pivot)")
    signal_kind = " + ".join(kinds) if kinds else ""

    out = {
        "identified": bool(signal or already),
        "signal_kind": signal_kind,
        "signal_date": str(signal["date"].date()) if signal else "",
        "signal_px": round(signal["close"], 2) if signal else None,
        "validated_entry_date": str(first_validated["date"].date()) if first_validated else "",
        "ep_date": str(first_ep["date"].date()) if first_ep else "",
        "total_peak_gain_pct": round(total_peak_gain * 100, 1) if total_peak_gain == total_peak_gain else None,
        "remaining_at_signal_pct": None,
        "timeliness": None,
    }

    if signal:
        peak_after = _peak_after(df, signal["date"], end)
        remaining = (peak_after / signal["close"] - 1) if signal["close"] > 0 else float("nan")
        out["remaining_at_signal_pct"] = round(remaining * 100, 1)
        tl = remaining / total_peak_gain if total_peak_gain and total_peak_gain > 0 else 0.0
        out["timeliness"] = round(min(max(tl, 0.0), 1.0), 2)

    # ---- the label ----
    if signal:
        tl = out["timeliness"] or 0.0
        if already and not (first_validated or first_ep) and first_confirmed is None:
            label, note = "ALREADY FLAGGED", "CONFIRMED before the window — on the radar/actionable panel, no fresh alert"
        elif tl >= EARLY_FRAC:
            label = "CAUGHT EARLY"
            note = "flagged with most of the move still ahead"
        elif tl >= LATE_FRAC:
            label = "CAUGHT"
            note = "flagged mid-move"
        else:
            label = "CAUGHT LATE"
            note = "flagged, but most of the move was already gone"
        if already and signal:
            note = "already CONFIRMED entering the window; " + note
    elif already:
        label, note = "ALREADY FLAGGED", "CONFIRMED before the window opened — on the radar the whole time, no fresh transition alert"
    else:
        # never identified — WHY? (all honest, mostly by-design)
        n_young = sum(1 for r in timeline if r["tag"] == "(young)")
        if n_young >= max(1, len(timeline) * 0.5):
            label, note = "TOO YOUNG", f"<{MIN_ROWS} bars for most of the window — no base can form (EP is the only path; EP {'fired' if first_ep else 'did not fire'})"
        elif "EXTENDED" in tags_seen and "CONFIRMED" not in tags_seen:
            label = "EXTENDED / NO ENTRY"
            note = ("in a straight-up run (EXTENDED) — deliberately not chased; the "
                    "intended entry is an EXTENDED->pullback re-entry that never set up")
            if first_antic:
                note += "; was on the ANTICIPATION watchlist first (zero-capital tier)"
        elif first_antic:
            label, note = "ANTICIPATION ONLY", "reached the Stage-1 watchlist tier (zero-capital by design) but never CONFIRMED"
        elif tags_seen <= {"WATCH", "BROKEN", "(young)", "(err)"}:
            label, note = "NO STRUCTURE", "never passed the Stage-2 8-point trend template — did not meet the mechanical uptrend gate"
        else:
            label, note = "MISSED", "taggable + eligible, structure present, yet never CONFIRMED/entry/EP — investigate (candidate pre-registered hypothesis)"

    out["classification"] = label
    out["note"] = note
    return out


# --------------------------------------------------------------------------- #
# orchestration
# --------------------------------------------------------------------------- #
def audit_window(symbols: list[str], bench: pd.DataFrame, end: pd.Timestamp,
                 win_key: str, top: int, explicit: bool) -> dict:
    start = end - pd.Timedelta(days=WINDOW_DAYS[win_key])

    if explicit:
        movers = []
        for sym in symbols:
            df = load_ohlcv(sym)
            if df is None or df.empty:
                movers.append({"symbol": sym, "return_pct": None, "end_px": None,
                               "start_px": None, "turnover_cr": None,
                               "_not_in_cache": True})
                continue
            wr = window_return(df, start, end)
            if wr is None:
                movers.append({"symbol": sym, "return_pct": None, "end_px": None,
                               "start_px": None, "turnover_cr": None,
                               "_young": True})
                continue
            ret, end_px, start_px, turnover_cr = wr
            movers.append({"symbol": sym, "return_pct": round(ret * 100, 1),
                           "end_px": round(end_px, 2), "start_px": round(start_px, 2),
                           "turnover_cr": round(turnover_cr, 2)})
        young = []
    else:
        movers, young = select_movers(symbols, start, end, top)

    results = []
    for rank, m in enumerate(movers, 1):
        sym = m["symbol"]
        if m.get("_not_in_cache"):
            results.append({**m, "rank": rank, "classification": "NOT_IN_UNIVERSE",
                            "identified": False, "signal_kind": "", "note": "not in the watched universe / price cache"})
            continue
        df = load_ohlcv(sym)
        if m.get("_young"):
            results.append({**m, "rank": rank, "classification": "TOO YOUNG",
                            "identified": False, "signal_kind": "",
                            "note": "listed after the window opened — no start price"})
            continue
        timeline, prior_tag = asof_timeline(df, bench, start, end)
        cls = classify(df, timeline, prior_tag, start, end, m["start_px"])
        results.append({**m, "rank": rank, **cls})

    return {"window": win_key, "start": str(start.date()), "end": str(end.date()),
            "results": results, "young_listings": young}


def append_journal(audit_date: str, windows: list[dict]) -> None:
    """Idempotent per audit_date: this journal is a periodic SNAPSHOT (one
    row-set per date), not an event log — a re-run on the same date REPLACES
    that date's rows so a manual or cloud retry can't duplicate the
    weekly-review series. Other dates are preserved (the history)."""
    os.makedirs(os.path.dirname(JOURNAL_CSV), exist_ok=True)
    rows = []
    for win in windows:
        for r in win["results"]:
            rows.append({
                "audit_date": audit_date, "window": win["window"],
                "rank": r.get("rank"), "symbol": r.get("symbol"),
                "window_return_pct": r.get("return_pct"),
                "turnover_cr": r.get("turnover_cr"),
                "classification": r.get("classification"),
                "identified": r.get("identified"),
                "signal_kind": r.get("signal_kind", ""),
                "signal_date": r.get("signal_date", ""),
                "signal_px": r.get("signal_px", ""),
                "remaining_at_signal_pct": r.get("remaining_at_signal_pct", ""),
                "total_peak_gain_pct": r.get("total_peak_gain_pct", ""),
                "timeliness": r.get("timeliness", ""),
                "validated_entry_date": r.get("validated_entry_date", ""),
                "ep_date": r.get("ep_date", ""),
                "note": r.get("note", ""),
            })
    fresh = pd.DataFrame(rows, columns=JOURNAL_FIELDS)
    if os.path.exists(JOURNAL_CSV):
        prior = pd.read_csv(JOURNAL_CSV, dtype=str)
        prior = prior[prior["audit_date"] != audit_date]  # drop this date's stale rows
        fresh = pd.concat([prior, fresh], ignore_index=True)
    fresh.to_csv(JOURNAL_CSV, index=False, quoting=csv.QUOTE_MINIMAL)


CAUGHT_LABELS = {"CAUGHT EARLY", "CAUGHT", "CAUGHT LATE", "ALREADY FLAGGED"}


def recall_line(results: list[dict]) -> str:
    eligible = [r for r in results if r["classification"] != "NOT_IN_UNIVERSE"]
    caught = [r for r in eligible if r["classification"] in CAUGHT_LABELS]
    n = len(eligible)
    return (f"{len(caught)}/{n} identified as buyable at some point "
            f"({sum(1 for r in eligible if r['classification'] in ('CAUGHT EARLY','CAUGHT'))} "
            f"early/mid, {sum(1 for r in eligible if r['classification']=='CAUGHT LATE')} late, "
            f"{sum(1 for r in eligible if r['classification']=='ALREADY FLAGGED')} already-standing)")


def write_report(audit_date: str, windows: list[dict]) -> None:
    L = []
    L.append(f"# Top-mover capture-recall audit — {audit_date}\n")
    L.append("**Recall is a DIAGNOSTIC, not the objective.** The system optimizes")
    L.append("risk-adjusted expectancy (VALIDATION_REPORT.md), deliberately not recall.")
    L.append("Every mover is classified with a reason; only **MISSED** is a real defect.")
    L.append("Movers are ranked within the 651-name watched universe. Prices are")
    L.append("as-of the latest completed bar in the local cache.\n")
    L.append("Labels: **CAUGHT EARLY** (flagged with most of the move ahead) · "
             "**CAUGHT** (mid-move) · **CAUGHT LATE** (most of the move gone) · "
             "**ALREADY FLAGGED** (CONFIRMED before the window — on the radar, no "
             "fresh alert) · **EXTENDED / NO ENTRY** (straight-up, deliberately not "
             "chased) · **ANTICIPATION ONLY** (watchlist tier, zero capital) · "
             "**TOO YOUNG** (<260 bars, only the EP class can fire) · "
             "**NO STRUCTURE** (never passed the trend template) · **MISSED** (defect).\n")

    for win in windows:
        res = win["results"]
        L.append(f"\n## {win['window']} window  ({win['start']} → {win['end']})\n")
        L.append(f"_Recall: {recall_line(res)}_\n")
        L.append("| # | Symbol | Return | Class | Identified when | Signal | Move left at signal | Note |")
        L.append("|--:|--------|-------:|-------|-----------------|--------|--------------------:|------|")
        for r in res:
            when = r.get("signal_date") or "—"
            sig = r.get("signal_kind") or "—"
            left = r.get("remaining_at_signal_pct")
            left_s = f"+{left}%" if isinstance(left, (int, float)) else "—"
            ret = r.get("return_pct")
            ret_s = f"+{ret}%" if isinstance(ret, (int, float)) else "—"
            L.append(f"| {r.get('rank')} | **{r['symbol']}** | {ret_s} | "
                     f"{r['classification']} | {when} | {sig} | {left_s} | {r.get('note','')} |")
        if win.get("young_listings"):
            yl = ", ".join(f"{y['symbol']} (+{y['since_listing_pct']}% since {y['listed']})"
                           for y in win["young_listings"][:6])
            L.append(f"\n_Young listings that IPO'd mid-window (no start price, ranked "
                     f"separately — the EP class is their only entry path): {yl}._")

    L.append("\n---\n")
    L.append("### How to read this")
    L.append("- **ALREADY FLAGGED / CAUGHT EARLY** = the system did its job.")
    L.append("- **EXTENDED / NO ENTRY** = the mover never paused; chasing it would")
    L.append("  violate the risk rule. The intended catch is the pullback re-entry.")
    L.append("- **TOO YOUNG / NO STRUCTURE** = structurally outside the strategy")
    L.append("  (young IPO, or never a Stage-2 trend). Expected non-catches.")
    L.append("- **MISSED** is the only line that should prompt a fix — and the fix is")
    L.append("  a *pre-registered hypothesis*, never a quiet threshold nudge.")
    with open(REPORT_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--windows", default="1w,1m,3m,6m",
                    help="comma list from " + ",".join(WINDOW_DAYS))
    ap.add_argument("--top", type=int, default=7)
    ap.add_argument("--symbols", nargs="*", default=None,
                    help="audit these exact names instead of ranking the universe")
    ap.add_argument("--no-journal", action="store_true")
    args = ap.parse_args()

    end = anchor_date()
    bench = load_ohlcv(BENCH)
    win_keys = [w.strip() for w in args.windows.split(",") if w.strip() in WINDOW_DAYS]
    if not win_keys:
        raise SystemExit("no valid windows")

    if args.symbols:
        symbols, explicit = args.symbols, True
    else:
        symbols, explicit = load_universe()["symbol"].tolist(), False

    windows = [audit_window(symbols, bench, end, wk, args.top, explicit) for wk in win_keys]
    audit_date = str(end.date())

    write_report(audit_date, windows)
    os.makedirs(os.path.dirname(STATE_JSON), exist_ok=True)
    with open(STATE_JSON, "w", encoding="utf-8") as f:
        json.dump({"audit_date": audit_date, "generated_at": datetime.now().isoformat(timespec="seconds"),
                   "windows": windows}, f, indent=1, default=str)
    if not args.no_journal:
        append_journal(audit_date, windows)

    # console summary
    for win in windows:
        print(f"\n=== {win['window']} ({win['start']} -> {win['end']}) ===")
        print("recall:", recall_line(win["results"]))
        for r in win["results"]:
            ret = r.get("return_pct")
            ret_s = f"+{ret}%" if isinstance(ret, (int, float)) else "  -  "
            print(f"  {r.get('rank'):>2} {r['symbol']:<12} {ret_s:>8}  "
                  f"{r['classification']:<18} {r.get('signal_kind','') or '-':<26} "
                  f"{('sig '+r['signal_date']) if r.get('signal_date') else ''}")
    print(f"\nreport  -> {os.path.relpath(REPORT_MD, PROJECT_ROOT)}")
    print(f"journal -> {os.path.relpath(JOURNAL_CSV, PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
