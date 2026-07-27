"""
scripts/penny_scan.py — rank the penny / nano-cap universe and journal it.

Pipeline (all of it reads the local cache; the only network step is the
optional incremental price update):

    penny_universe.csv                (hard tradability gates already applied)
      -> incremental Yahoo price update
      -> per-name technicals: stage tag, trend template, RS *within the penny
         universe*, 52-week position, volume expansion, episodic pivot
      -> penny_fundamentals.csv       (screener.in, shared page cache)
      -> scoring/penny_score.assess_penny
      -> penny_ranked.csv · state/penny_details.json · penny_report.md
      -> journal/penny_journal.csv    (append-only forward record)

RS is ranked WITHIN the penny universe on purpose: a nano-cap's relevant peer
set is other nano-caps, not the Nifty Midcap 150. The benchmark for the raw
ratio stays NIFTY50 (it is the market), but the percentile is local.

Nothing here feeds the validated system. No alert fires, no position is sized,
no capital is implied. The journal exists so that in three months there is a
NUMBER instead of an opinion about whether this screen adds anything.

    python scripts/penny_scan.py                 # full run
    python scripts/penny_scan.py --no-update     # skip the price fetch
    python scripts/penny_scan.py --top 25
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

from build_penny_universe import recheck_caps
from config import PENNY
from data.cache import load_ohlcv
from scoring.penny_score import assess_penny
from scoring.stage_tagger import rs_metrics, tag_stock
from scoring.technical_score import (compute_atr, detect_episodic_pivot,
                                     evaluate_trend_template,
                                     add_moving_averages)
from update_prices import update_symbols

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UNIVERSE = os.path.join(ROOT, "penny_universe.csv")
FUNDAMENTALS = os.path.join(ROOT, "penny_fundamentals.csv")
OUT_RANKED = os.path.join(ROOT, "penny_ranked.csv")
OUT_DETAILS = os.path.join(ROOT, "state", "penny_details.json")
OUT_REPORT = os.path.join(ROOT, "penny_report.md")
JOURNAL = os.path.join(ROOT, "journal", "penny_journal.csv")

JOURNAL_FIELDS = ["logged_at", "run_date", "symbol", "rank", "score", "coverage_pct",
                  "vetoed", "veto_reasons", "archetypes", "close", "atr",
                  "stop_suggested", "tag", "rs_pctile", "median_turnover_cr",
                  "market_cap_cr", "risk_flags"]

MIN_BARS_FOR_STAGE = 260


def _json_safe(o):
    """json.dump fallback: numpy scalars -> python numbers, everything else
    -> str. Without this a numpy.float64 becomes the STRING "96.9"."""
    if hasattr(o, "item"):
        try:
            return o.item()
        except (ValueError, AttributeError):
            pass
    if isinstance(o, float) and o != o:      # NaN
        return None
    return str(o)


def technicals(symbols: list[str]) -> dict[str, dict]:
    """Per-symbol technical read + the RS percentile ranked within this
    universe. Names with too little history still get what can be computed."""
    bench = load_ohlcv("NIFTY50")
    raw: dict[str, dict] = {}
    rs_blends: dict[str, float] = {}

    for sym in symbols:
        df = load_ohlcv(sym)
        if df is None or len(df) < 60:
            continue
        t: dict = {"bars": len(df), "last_close": float(df["close"].iloc[-1]),
                   "last_date": str(df["date"].iloc[-1].date())}
        try:
            t["ep"] = detect_episodic_pivot(df)
        except Exception:  # noqa: BLE001 — one bad frame must not kill the scan
            t["ep"] = None

        if bench is not None:
            rs = rs_metrics(df, bench)
            if rs.get("rs_blend") is not None:
                rs_blends[sym] = rs["rs_blend"]
            t["rs_improving"] = rs.get("rs_improving")

        hi52 = float(df["high"].tail(252).max())
        if hi52 > 0:
            t["pct_below_52w_high"] = round((1 - t["last_close"] / hi52) * 100, 1)
        if len(df) > 63:
            t["run_3m_pct"] = round(
                (t["last_close"] / float(df["close"].iloc[-64]) - 1) * 100, 1)

        # volume EXPANSION in traded value, not shares (a penny stock's share
        # count says nothing; the rupees changing hands say everything)
        tv = (df["close"] * df["volume"])
        if len(tv) >= 90:
            base = float(tv.tail(90).mean())
            recent = float(tv.tail(20).mean())
            if base > 0:
                t["vol_expansion"] = round(recent / base, 2)

        if len(df) >= MIN_BARS_FOR_STAGE and bench is not None:
            try:
                tag = tag_stock(df, bench)
                t.update({"tag": tag["tag"], "tt_checks": tag["trend_template_checks_passed"],
                          "stage_name": tag["stage"].get("stage_name", ""),
                          "vcp_valid": tag.get("vcp_valid"),
                          "pivot_price": tag.get("pivot_price"),
                          "validated_entry": tag.get("validated_entry"),
                          "reasons": tag.get("reasons", [])})
            except Exception as e:  # noqa: BLE001
                t["tag_error"] = str(e)[:60]
        else:
            dfm = add_moving_averages(df)
            tt = evaluate_trend_template(dfm)
            t["tt_checks"] = sum(bool(v) for v in tt.checks.values()) \
                if not tt.checks.get("insufficient_history") else 0
            t["tag"] = "YOUNG"

        try:
            atr = float(compute_atr(df).iloc[-1])
            t["atr"] = round(atr, 2) if atr == atr else None
        except Exception:  # noqa: BLE001
            t["atr"] = None
        raw[sym] = t

    if rs_blends:
        pct = (pd.Series(rs_blends).rank(pct=True) * 100).round(1)
        for sym, v in pct.items():
            raw[sym]["rs_pctile"] = float(v)
    return raw


def suggested_stop(close: float, atr: float | None, ep: dict | None) -> tuple[float | None, str]:
    """Reference stop for the forward journal ONLY — this is not a sized plan.
    Penny names are volatile enough that a 2.5xATR stop is routinely wider
    than the main system's 12% hard cap; when it is, the honest answer is
    'no tradeable stop', not a clamped one (Design Law #7)."""
    if ep and ep.get("stop_price"):
        stop = float(ep["stop_price"])
        return (stop, "episodic-pivot day low") if stop < close else (None, "EP stop invalid")
    if not atr or atr <= 0:
        return None, "no ATR"
    stop = close - 2.5 * atr
    width = (close - stop) / close * 100
    if width > 20:
        return None, f"2.5xATR stop would be {width:.0f}% wide — untradeably volatile"
    return round(stop, 2), f"2.5xATR ({width:.0f}% wide)"


def journal_append(rows: list[dict]) -> int:
    """Append-only, one row per (run_date, symbol) — a same-day re-run adds
    nothing (the main system's idempotence convention)."""
    if not rows:
        return 0
    os.makedirs(os.path.dirname(JOURNAL), exist_ok=True)
    seen: set[tuple[str, str]] = set()
    if os.path.exists(JOURNAL):
        try:
            old = pd.read_csv(JOURNAL)
            seen = set(zip(old["run_date"].astype(str), old["symbol"].astype(str)))
        except (ValueError, KeyError):
            seen = set()
    fresh = [r for r in rows if (str(r["run_date"]), str(r["symbol"])) not in seen]
    if not fresh:
        return 0
    new_file = not os.path.exists(JOURNAL)
    with open(JOURNAL, "a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=JOURNAL_FIELDS)
        if new_file:
            w.writeheader()
        for r in fresh:
            w.writerow({k: r.get(k, "") for k in JOURNAL_FIELDS})
    return len(fresh)


def run(no_update: bool = False, top: int = 20, recheck: bool = True) -> pd.DataFrame:
    if not os.path.exists(UNIVERSE):
        print("no penny_universe.csv — run scripts/build_penny_universe.py first")
        return pd.DataFrame()

    # SETTLE THE ARMS FIRST. The weekly chain is build_penny_universe ->
    # penny_fundamentals -> penny_scan, so the universe was assembled before
    # most market caps existed and a cheap share of a huge company can only be
    # spotted now, with the caps in hand. Doing it here rather than at the
    # build keeps the correction in the same run instead of a week later: on
    # 2026-07-26 the cloud shipped a "penny and nano-cap" universe whose #1
    # name was a Rs13,761 Cr bank, and it would have stayed that way until the
    # next weekend. No network — this reads the cache the previous step filled.
    if recheck:
        try:
            if recheck_caps() is None:
                print("  (no gate snapshot yet — universe used as built; "
                      "the next full build writes one)", flush=True)
        except Exception as e:  # noqa: BLE001 — research surface, never fatal
            print(f"  cap re-check skipped: {str(e)[:90]}", flush=True)

    uni = pd.read_csv(UNIVERSE)
    symbols = uni["symbol"].tolist()
    print(f"penny scan: {len(symbols)} names (universe as of "
          f"{uni['as_of'].iloc[0] if 'as_of' in uni.columns and len(uni) else '?'})",
          flush=True)

    if not no_update:
        print("updating prices...", flush=True)
        ok, fail = update_symbols(symbols + ["NIFTY50"], pause=0.25)
        print(f"  {ok} updated, {len(fail)} failed", flush=True)

    tech = technicals(symbols)
    print(f"technicals computed for {len(tech)}/{len(symbols)}", flush=True)

    fund_by_sym: dict[str, dict] = {}
    if os.path.exists(FUNDAMENTALS):
        fdf = pd.read_csv(FUNDAMENTALS)
        fund_by_sym = {r["symbol"]: {k: v for k, v in r.items() if pd.notna(v)}
                       for _, r in fdf.iterrows()}
        print(f"fundamentals available for {len(fund_by_sym)} names", flush=True)

    uni_by_sym = {r["symbol"]: dict(r) for _, r in uni.iterrows()}

    rows, details = [], {}
    for sym in symbols:
        t = tech.get(sym)
        u = uni_by_sym.get(sym)
        f = fund_by_sym.get(sym)
        read = assess_penny(sym, f, t, u)
        close = (t or {}).get("last_close") or (u or {}).get("last_close")
        stop, stop_basis = suggested_stop(float(close), (t or {}).get("atr"),
                                          (t or {}).get("ep")) if close else (None, "")
        rows.append({
            "symbol": sym,
            "company": (u or {}).get("company", ""),
            "score": read.score, "coverage_pct": read.coverage_pct,
            "vetoed": read.vetoed, "assessed": read.assessed,
            "veto_reasons": "; ".join(read.veto_reasons),
            "archetypes": " + ".join(read.archetypes),
            "arm": (u or {}).get("arm", ""),
            "close": close, "tag": (t or {}).get("tag", ""),
            "rs_pctile": (t or {}).get("rs_pctile"),
            "tt_checks": (t or {}).get("tt_checks"),
            "pct_below_52w_high": (t or {}).get("pct_below_52w_high"),
            "run_3m_pct": (t or {}).get("run_3m_pct"),
            "vol_expansion": (t or {}).get("vol_expansion"),
            "ep": bool((t or {}).get("ep")),
            "market_cap_cr": (f or {}).get("market_cap_cr"),
            "median_turnover_cr": (u or {}).get("median_turnover_cr"),
            "median_trades": (u or {}).get("median_trades"),
            "band_pct": (u or {}).get("band_pct"),
            "circuit_frac": (u or {}).get("circuit_frac"),
            "in_index_universe": (u or {}).get("in_index_universe"),
            "atr": (t or {}).get("atr"),
            "stop_suggested": stop, "stop_basis": stop_basis,
            "risk_flags": " | ".join(read.risk_flags),
        })
        details[sym] = {
            "scored_at": datetime.now().strftime("%Y-%m-%d"),
            "score": read.score, "coverage": read.coverage_pct,
            "label": read.label, "vetoed": read.vetoed,
            "veto_reasons": read.veto_reasons, "risk_flags": read.risk_flags,
            "archetypes": read.archetypes,
            "blocks": [{"k": b["key"], "w": b["weight"], "s": b["score"],
                        "live": b["live"], "n": str(b["notes"])[:260]}
                       for b in read.blocks],
            "tag": (t or {}).get("tag"), "rs": (t or {}).get("rs_pctile"),
            "close": close, "stop": stop, "stop_basis": stop_basis,
            "ep": (t or {}).get("ep"),
            "reasons": (t or {}).get("reasons", []),
            "pivot_price": (t or {}).get("pivot_price"),
        }

    df = pd.DataFrame(rows)
    # THREE TIERS, in this order (audit 2026-07-25):
    #   0  assessed + clean   — the survival screen ran and found nothing fatal
    #   1  NOT ASSESSED       — fundamentals unreadable, so no veto could fire
    #   2  vetoed             — checked and failed
    # Tier 1 used to rank inside tier 0 and dominated the top of the table:
    # unexamined names carry no penalties, so renormalizing over the surviving
    # momentum blocks floats them upward. Not knowing is not a virtue.
    df["tier"] = df["vetoed"].astype(int) * 2 + (~df["assessed"]).astype(int)
    df.loc[df["vetoed"], "tier"] = 2
    df = df.sort_values(["tier", "score"], ascending=[True, False],
                        na_position="last").reset_index(drop=True)
    df["rank"] = df.index + 1
    df.to_csv(OUT_RANKED, index=False)

    os.makedirs(os.path.dirname(OUT_DETAILS), exist_ok=True)
    with open(OUT_DETAILS, "w", encoding="utf-8") as fh:
        # numpy scalars are not JSON-serializable and would silently fall
        # through to str(), turning numbers into strings the dashboard then
        # cannot do arithmetic on
        json.dump(details, fh, default=_json_safe)

    # forward record: the top N non-vetoed, scorable names
    run_date = datetime.now().strftime("%Y-%m-%d")
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    jrows = []
    # only tier 0 is journaled — an unexamined name is not a forward "pick",
    # and logging it as one would put the same bias into the forward record
    # that the tier split just took out of the table
    for _, r in df[(df["tier"] == 0) & df["score"].notna()].head(top).iterrows():
        jrows.append({"logged_at": now, "run_date": run_date, "symbol": r["symbol"],
                      "rank": int(r["rank"]), "score": r["score"],
                      "coverage_pct": r["coverage_pct"], "vetoed": r["vetoed"],
                      "veto_reasons": r["veto_reasons"], "archetypes": r["archetypes"],
                      "close": r["close"], "atr": r["atr"],
                      "stop_suggested": r["stop_suggested"], "tag": r["tag"],
                      "rs_pctile": r["rs_pctile"],
                      "median_turnover_cr": r["median_turnover_cr"],
                      "market_cap_cr": r["market_cap_cr"],
                      "risk_flags": r["risk_flags"]})
    n_journal = journal_append(jrows)

    write_report(df, top)
    print(f"\n-> {OUT_RANKED} ({len(df)} names)")
    print(f"-> {OUT_DETAILS}")
    print(f"-> {OUT_REPORT}")
    print(f"-> {n_journal} new row(s) in {JOURNAL}")
    return df


def write_report(df: pd.DataFrame, top: int) -> None:
    live = df[(df["tier"] == 0) & df["score"].notna()]
    unassessed = df[df["tier"] == 1]
    vetoed = df[df["vetoed"]]
    lines = [
        f"# Penny / nano-cap screen — {datetime.now():%Y-%m-%d %H:%M}",
        "",
        "**Research surface. Zero capital. Not backtested.** The main system's",
        "evidence (+1.67R, walk-forward, 13 rejected overlays) says nothing about",
        "this screen. Every name below is journaled to `journal/penny_journal.csv`",
        "so the question 'does this add anything?' gets an out-of-sample answer",
        "instead of an argument.",
        "",
        f"Universe: {len(df)} names that survived the hard tradability gates",
        "(EQ series only · no GSM/ASM · band >= 10% · liquidity + circuit floors ·",
        f"listed >= 1 year). Rejects and their reasons: `penny_excluded.csv`.",
        "",
        f"Suggested exposure discipline: <= {PENNY.suggested_max_book_pct:.0f}% of the book in",
        f"this class in total, <= {PENNY.suggested_max_position_pct:.0f}% in any one name.",
        "",
        "The **arm** column matters: PRICE means only that the share costs under",
        "Rs100 — a Rs40 share of a Rs9,000 Cr bank is not a small company. MCAP is",
        "the one that means genuinely small. Read the MCAP rows first.",
        "",
        f"## Top {top}",
        "",
        "| # | Symbol | Arm | Score | Cov | Stage | RS | Turnover | Cap | Archetype | Risk flags |",
        "|--:|--------|-----|------:|----:|-------|---:|---------:|----:|-----------|-----------|",
    ]
    for _, r in live.head(top).iterrows():
        cap = f"Rs{r['market_cap_cr']:.0f} Cr" if pd.notna(r.get("market_cap_cr")) else "—"
        rs = f"{r['rs_pctile']:.0f}" if pd.notna(r.get("rs_pctile")) else "—"
        flags = str(r.get("risk_flags") or "")
        n_flags = len([x for x in flags.split("|") if x.strip()])
        lines.append(
            f"| {int(r['rank'])} | **{r['symbol']}** | {str(r.get('arm') or '—').upper()} | "
            f"{r['score']:.0f} | {r['coverage_pct']:.0f}% | {r.get('tag') or '—'} | "
            f"{rs} | Rs{r['median_turnover_cr']:.2f} Cr | {cap} | "
            f"{r.get('archetypes') or '—'} | {n_flags or '—'} |")
    if len(unassessed):
        lines += ["", f"## Not assessed ({len(unassessed)})",
                  "",
                  "Their screener.in page carried no readable financials, so **none of",
                  "the survival vetoes could run** — no pledge check, no dilution check,",
                  "no shell check. They are ranked below every assessed name and kept",
                  "out of the journal, because an unexamined company is not a clean one.",
                  "They heal automatically once the page parses "
                  "(`scripts/heal_fundamentals_cache.py`).",
                  "", "| Symbol | Arm | Stage | RS | What is missing |",
                  "|--------|-----|-------|---:|-----------------|"]
        for _, r in unassessed.head(25).iterrows():
            rs = f"{r['rs_pctile']:.0f}" if pd.notna(r.get("rs_pctile")) else "—"
            lines.append(f"| {r['symbol']} | {str(r.get('arm') or '—').upper()} | "
                         f"{r.get('tag') or '—'} | {rs} | fundamentals unreadable |")
    if len(vetoed):
        lines += ["", f"## Vetoed ({len(vetoed)}) — capped at 25, momentum cannot outvote these",
                  "", "| Symbol | Reason |", "|--------|--------|"]
        for _, r in vetoed.head(25).iterrows():
            lines.append(f"| {r['symbol']} | {str(r['veto_reasons'])[:150]} |")
    lines += ["", "---", "",
              "### What would make this trustworthy",
              "A pre-registered backtest of this screen on the penny universe, run",
              "through `backtest/engine.py` with the same two-lot rules and costs,",
              "compared against the technical-only baseline. Until that exists these",
              "are ideas with a liquidity check, not signals."]
    with open(OUT_REPORT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-update", action="store_true")
    ap.add_argument("--top", type=int, default=20)
    ap.add_argument("--no-recheck", action="store_true",
                    help="do not re-settle the universe arms against newly "
                         "cached market caps before ranking")
    args = ap.parse_args()
    run(no_update=args.no_update, top=args.top, recheck=not args.no_recheck)


if __name__ == "__main__":
    main()
