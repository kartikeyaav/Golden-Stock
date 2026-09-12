"""
scripts/update_prices.py — incremental price updates for cached symbols:
fetch only from (last cached date - 7d) to now and merge into the cache
(cache.save_ohlcv dedupes). Symbols not yet cached get a full backfill.

    python scripts/update_prices.py --focus       # focus list + holdings + benchmark
    python scripts/update_prices.py --all         # whole universe.csv
    python scripts/update_prices.py SUZLON BSE    # explicit
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from datetime import datetime, timedelta

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import GATE
from data.cache import CACHE_DIR, load_manifest
from data.yahoo_loader import fetch_yahoo_daily
from data.cache import save_ohlcv

FULL_BACKFILL_START = "2019-01-01"
# NIFTY50 is the RS benchmark the scoring uses. GATE.benchmark_symbol is the
# capital gate's "dumb alternative" — a momentum-quality mid/small-cap ETF you
# could buy instead of running any of this (CAPITAL_GATE.md §4 condition 2).
# Its TRADED price is what we want, tracking error and expenses included.
_SPECIAL_YAHOO = {"NIFTY50": "^NSEI", GATE.benchmark_symbol: GATE.benchmark_yahoo}
# every price refresh keeps both benchmarks current, so the gate can never be
# evaluated against a stale comparator
BENCHMARK_SYMBOLS = ["NIFTY50", GATE.benchmark_symbol]
# if the fresh fetch disagrees with the cached history on the overlap window by
# more than this, Yahoo has re-adjusted the whole series (split/bonus) and our
# cached history is at the OLD scale — beyond any circuit band, so it can only
# be a corporate action, not a real move.
_ADJ_BAND = 0.30
# above this share of failed symbols the run is a broken feed, not a bad night
_FAIL_FRACTION_FATAL = 0.20


def _adjustment_detected(sym: str, fresh: pd.DataFrame) -> float | None:
    """Compare the fresh incremental fetch against cached closes on overlapping
    dates. Yahoo split-adjusts the ENTIRE series retroactively, so after a
    split the overlap ratio jumps to the split factor. Returns the median
    ratio when it deviates past the band (a corporate action), else None."""
    path = CACHE_DIR / f"{sym}.csv"
    if not path.exists() or fresh.empty:
        return None
    try:
        old = pd.read_csv(path, parse_dates=["date"])[["date", "close"]]
    except (ValueError, KeyError, OSError):
        return None
    f = fresh.copy()
    f.columns = [str(c).lower() for c in f.columns]
    if "date" not in f or "close" not in f:
        return None
    f["date"] = pd.to_datetime(f["date"])
    merged = old.merge(f[["date", "close"]], on="date", suffixes=("_old", "_new"))
    merged = merged[(merged["close_old"] > 0) & (merged["close_new"] > 0)]
    if len(merged) < 2:
        return None
    med = float((merged["close_new"] / merged["close_old"]).median())
    return med if abs(med - 1.0) > _ADJ_BAND else None


# How far the exchange's own previous close may sit from our cached close
# before the two are judged to be on different scales. The measured agreement
# on 2026-09-07 was 1,020 of 1,020 names inside this band.
_TOPUP_BAND = 0.005


def topup_from_bhavcopy(symbols: list[str], bhav=None,
                        prev_session=None) -> dict:
    """Fill the newest session from NSE's own file for names Yahoo has not
    published yet. Adopted 2026-09-12 — PREREG_2026-09-12_bhavcopy.md.

    Yahoo publishes this universe a session late for most of it: on 2026-09-12,
    611 of 1,028 names still had no bar for the 09-11 session 22 hours after
    the close, while the exchange's bhavcopy for that session carried 2,637 EQ
    rows. Tags computed on a stale close are a day-late transition and a
    day-late alert.

    Four rules keep a raw source from corrupting a split-adjusted history:

      * ONE session per run — the newest bhavcopy, never a backfill.
      * Only for a symbol already holding the session before it. A name
        further behind waits for Yahoo, because a multi-session gap can hide a
        corporate action.
      * Only when the exchange's own `prev_close` matches our cached last
        close within `_TOPUP_BAND`. This is the scale test: after a split
        NSE's prev_close is adjusted while our Yahoo history is still at the
        old scale, the ratio lands far outside the band, and the name is left
        for Yahoo's full re-adjusted refetch instead of being handed a raw bar.
      * EQ series only.

    Yahoo keeps precedence on every date it eventually publishes:
    `normalize_ohlcv` dedupes keep='last' and the Yahoo pass runs first.
    """
    from data.cache import load_ohlcv, save_ohlcv
    stats = {"session": None, "filled": 0, "scale_skip": 0, "behind_skip": 0,
             "absent": 0, "current": 0, "scale_names": []}
    if bhav is None:
        from datetime import date as _date
        from data.nse_all import bhavcopy
        d = _date.today()
        for _ in range(7):
            if d.weekday() < 5:
                got = bhavcopy(d)
                if got is not None and len(got):
                    bhav = got
                    break
            d -= timedelta(days=1)
    if bhav is None or not len(bhav):
        return stats
    if prev_session is None:
        # the previous session per the exchange, so "one behind" is a calendar
        # fact rather than an inference from a weekend or a holiday
        from datetime import date as _date2
        from data.nse_all import bhavcopy as _bh
        _d = pd.Timestamp(bhav["date"].iloc[0]).date() - timedelta(days=1)
        for _ in range(7):
            if _d.weekday() < 5:
                _got = _bh(_d)
                if _got is not None and len(_got):
                    prev_session = _d
                    break
            _d -= timedelta(days=1)

    b = bhav[bhav["series"].astype(str).str.strip() == "EQ"].copy()
    if not len(b):
        return stats
    session = pd.Timestamp(b["date"].iloc[0]).normalize()
    stats["session"] = str(session.date())
    rows = {str(r["symbol"]).strip(): r for _, r in b.iterrows()}

    for sym in symbols:
        row = rows.get(sym)
        if row is None:
            stats["absent"] += 1
            continue
        cached = load_ohlcv(sym)
        if cached is None or cached.empty:
            stats["absent"] += 1
            continue
        last = pd.Timestamp(cached["date"].iloc[-1]).normalize()
        if last >= session:
            stats["current"] += 1
            continue
        # EXACTLY ONE SESSION BEHIND — checked against the exchange's own
        # calendar, not against prices. The first version of this only compared
        # prev_close, and 136 names whose 09-07 close happened to sit within
        # 0.5% of the 09-10 close were handed a 09-11 bar straight onto a
        # three-session hole. Agreement by coincidence is not adjacency.
        if prev_session is not None and last != pd.Timestamp(prev_session).normalize():
            stats["behind_skip"] += 1
            continue
        prev = pd.to_numeric(pd.Series([row.get("prev_close")]), errors="coerce").iloc[0]
        have = float(cached["close"].iloc[-1])
        if pd.isna(prev) or not have:
            stats["behind_skip"] += 1
            continue
        if abs(float(prev) - have) / have > _TOPUP_BAND:
            stats["scale_skip"] += 1
            if len(stats["scale_names"]) < 8:
                stats["scale_names"].append(sym)
            continue
        one = pd.DataFrame([{
            "date": session, "open": row["open"], "high": row["high"],
            "low": row["low"], "close": row["close"], "volume": row["volume"],
        }])
        save_ohlcv(sym, one, meta={"last_topup": str(session.date()),
                                   "last_topup_source": "nse_bhavcopy"})
        stats["filled"] += 1
    return stats


def run_topup(symbols: list[str]) -> dict:
    """Run the bhavcopy top-up and report it. Non-fatal by construction.

    A FUNCTION, not a block inside main(), because `daily_scan.py` imports
    `update_symbols` directly and never executes this module's main() — a
    top-up living in main() would have shipped, passed its tests, and simply
    never run on the job it was written for. tests/test_bhavcopy_seam.py pins
    the wiring so it cannot quietly come loose again."""
    try:
        t = topup_from_bhavcopy(symbols)
    except Exception as e:  # noqa: BLE001 — a price stopgap must never end a scan
        print(f"bhavcopy top-up degraded (non-fatal): {str(e)[:120]}", flush=True)
        return {"session": None, "filled": 0}
    if t["session"]:
        print(f"bhavcopy top-up for {t['session']}: filled {t['filled']}, "
              f"already current {t['current']}, absent {t['absent']}, "
              f"left for Yahoo {t['behind_skip'] + t['scale_skip']}"
              + (f" (scale mismatch: {', '.join(t['scale_names'])})"
                 if t["scale_names"] else ""), flush=True)
    else:
        print("bhavcopy top-up: no session available (NSE unreachable?)", flush=True)
    return t


def update_symbols(symbols: list[str], pause: float = 0.3) -> tuple[int, list[str]]:
    manifest = load_manifest()
    ok, failures, readjusted = 0, [], []
    for i, sym in enumerate(symbols, 1):
        yahoo_sym = _SPECIAL_YAHOO.get(sym) or manifest.get(sym, {}).get("yahoo_symbol") or f"{sym}.NS"
        last = manifest.get(sym, {}).get("last_date")
        start = (datetime.strptime(last, "%Y-%m-%d") - timedelta(days=7)).strftime("%Y-%m-%d") \
            if last else FULL_BACKFILL_START
        try:
            df = fetch_yahoo_daily(yahoo_sym, start)
            # corporate-action guard: on a split/bonus the incremental slice
            # comes back re-scaled vs our cached history -> a fake cliff that
            # would corrupt MAs/stage/ATR and fire a phantom BROKEN alert.
            # Refetch the FULL history (Yahoo returns it consistently adjusted);
            # the full span overwrites every old row on merge (keep=last).
            if last:
                ratio = _adjustment_detected(sym, df)
                if ratio is not None:
                    df = fetch_yahoo_daily(yahoo_sym, FULL_BACKFILL_START)
                    readjusted.append(sym)
                    print(f"[{i}/{len(symbols)}] CORP-ACTION {sym}: overlap x{ratio:.3f} "
                          f"-> full refetch (split/bonus)", flush=True)
            save_ohlcv(sym, df, meta={"source": "yahoo", "yahoo_symbol": yahoo_sym})
            ok += 1
        except Exception as e:  # noqa: BLE001
            failures.append(sym)
            print(f"[{i}/{len(symbols)}] FAIL {sym}: {str(e)[:60]}", flush=True)
        if i % 50 == 0:
            print(f"[{i}/{len(symbols)}] ...", flush=True)
        time.sleep(pause)
    if readjusted:
        print(f"corporate-action refetch: {len(readjusted)} symbol(s) -> {readjusted}", flush=True)
    return ok, failures


def universe_and_holdings_symbols(root: str) -> list[str]:
    """The FULL watch set. Matrix evidence (2026-07-06): the validated system
    entered breakouts from the whole universe — the daily scan must watch the
    whole universe too, or the focus-list filter becomes an untested gate."""
    symbols = list(BENCHMARK_SYMBOLS)
    universe_path = os.path.join(root, "universe.csv")
    if os.path.exists(universe_path):
        symbols += pd.read_csv(universe_path)["symbol"].tolist()
    holdings_path = os.path.join(root, "holdings.csv")
    if os.path.exists(holdings_path):
        symbols += pd.read_csv(holdings_path)["symbol"].tolist()
    seen, out = set(), []
    for s in symbols:
        if s not in seen:
            seen.add(s)
            out.append(s)
    return out


def focus_and_holdings_symbols(root: str) -> list[str]:
    symbols = list(BENCHMARK_SYMBOLS)
    focus_path = os.path.join(root, "focus_list.csv")
    if os.path.exists(focus_path):
        symbols += pd.read_csv(focus_path)["symbol"].tolist()
    holdings_path = os.path.join(root, "holdings.csv")
    if os.path.exists(holdings_path):
        symbols += pd.read_csv(holdings_path)["symbol"].tolist()
    seen, out = set(), []
    for s in symbols:
        if s not in seen:
            seen.add(s)
            out.append(s)
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("symbols", nargs="*")
    parser.add_argument("--focus", action="store_true")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--pause", type=float, default=0.3)
    args = parser.parse_args()

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if args.all:
        symbols = BENCHMARK_SYMBOLS + pd.read_csv(os.path.join(root, "universe.csv"))["symbol"].tolist()
    elif args.focus:
        symbols = focus_and_holdings_symbols(root)
    else:
        symbols = args.symbols
    if not symbols:
        parser.error("give symbols, --focus, or --all")

    t0 = time.time()
    ok, failures = update_symbols(symbols, pause=args.pause)
    # the exchange's own file closes the gap Yahoo leaves open (see
    # topup_from_bhavcopy). Non-fatal: if NSE is unreachable the run degrades
    # to exactly the behaviour it had before this existed.
    run_topup(symbols)
    print(f"updated {ok}/{len(symbols)} in {(time.time()-t0)/60:.1f} min"
          + (f"; failed: {len(failures)} -> {failures[:20]}"
             f"{'...' if len(failures) > 20 else ''}" if failures else ""))
    # Exit NON-ZERO on a broad failure. weekly_refresh runs this step with
    # fatal=True, which meant nothing while a run that failed 646 of 835
    # symbols still exited 0 and let the whole chain proceed on stale prices.
    # A handful of failures is normal (renamed/suspended names); most of the
    # universe failing is a broken feed and must stop the run.
    frac = len(failures) / max(1, len(symbols))
    if frac > _FAIL_FRACTION_FATAL:
        print(f"FATAL: {frac:.0%} of symbols failed to update — treating this as a "
              f"broken price feed rather than refreshing part of the universe "
              f"and reporting success", flush=True)
        sys.exit(1)
    if failures:
        print(f"note: {frac:.1%} failed — under the {_FAIL_FRACTION_FATAL:.0%} "
              f"fatal threshold, continuing")


if __name__ == "__main__":
    main()
