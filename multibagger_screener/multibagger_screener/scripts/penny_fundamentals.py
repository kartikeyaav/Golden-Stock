"""
scripts/penny_fundamentals.py — fundamentals for the penny universe.

Deliberately SEPARATE from scripts/fetch_fundamentals.py: that script rewrites
fundamentals_flat.csv, which the main system's shortlist scoring reads. Penny
names must never leak into that file. This one shares only the on-disk page
cache (fundamentals_cache/) — a cache hit costs nothing and a page fetched for
either purpose serves both.

Two jobs:
  1. resolve MARKET CAP for the "mcap pending" names, so the mcap arm of the
     universe can close (build_penny_universe.py holds them until then)
  2. pull the survival/quality series the penny score needs: pledge, promoter
     trend, dilution, sales/profit, debt, OPM

Politeness: a 7 s pause, cache-aware (skips anything fetched within
--max-age-days), and a bounded --limit so a run can be capped. screener.in
answers HTTP 429 after about 25 quick requests; at the old 1.8 s pause every
later name failed, and 56 of 154 penny names had no readable fundamentals,
so none of the survival vetoes could run on them (2026-10-14). On a 429 the
run waits (90 s, doubling) and retries the same name, and stops fetching
after five refusals in a row: the rest is picked up by the next run.

    python scripts/penny_fundamentals.py                 # universe, then pending
    python scripts/penny_fundamentals.py --limit 200
    python scripts/penny_fundamentals.py --pending-only
"""

from __future__ import annotations

import argparse
import os
import sys
import time

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.screener_fetch import (fetch_company, has_real_data, load_company,
                                 save_company)
from fetch_fundamentals import _age_days, flatten

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UNIVERSE = os.path.join(ROOT, "penny_universe.csv")
EXCLUDED = os.path.join(ROOT, "penny_excluded.csv")
OUT = os.path.join(ROOT, "penny_fundamentals.csv")

PAUSE_SECONDS = 7.0
MAX_REFUSALS = 5


def _series(data: dict, section: str, *labels: str) -> list:
    rows = (data.get(section) or {}).get("rows") or {}
    for lb in labels:
        if rows.get(lb):
            return [v for v in rows[lb]]
    return []


def penny_extras(data: dict) -> dict:
    """Fields the penny score needs that the shared `flatten()` does not
    expose. Derived from the SAME cached page JSON — deliberately computed
    here instead of extending flatten(), because flatten() feeds
    fundamentals_flat.csv and the validated shortlist scoring reads that file.

    - sales_ttm_cr / sales_yoy_q: the shell test. A "company" with Rs2 Cr of
      trailing sales is a listed shell whatever its chart looks like, and the
      quarterly Sales row is the only place that shows up.
    - net_worth_cr: negative net worth is terminal, and common down here.
    """
    out: dict = {}
    sales = [v for v in _series(data, "quarters", "Sales", "Revenue") if v is not None]
    if len(sales) >= 4:
        out["sales_ttm_cr"] = round(sum(sales[-4:]), 2)
        out["sales_latest_cr"] = sales[-1]
        if len(sales) >= 5 and sales[-5]:
            out["sales_yoy_q"] = round((sales[-1] / sales[-5] - 1) * 100, 1)
    elif sales:
        out["sales_latest_cr"] = sales[-1]

    eq = [v for v in _series(data, "balance_sheet", "Equity Capital") if v is not None]
    res = [v for v in _series(data, "balance_sheet", "Reserves") if v is not None]
    if eq and res:
        out["reserves_cr"] = res[-1]
        out["net_worth_cr"] = round(eq[-1] + res[-1], 2)
    return out


def target_symbols(pending_only: bool = False) -> list[str]:
    syms: list[str] = []
    if not pending_only and os.path.exists(UNIVERSE):
        syms += pd.read_csv(UNIVERSE)["symbol"].tolist()
    if os.path.exists(EXCLUDED):
        ex = pd.read_csv(EXCLUDED)
        if "mcap_pending" in ex.columns:
            pend = ex[ex["mcap_pending"].astype(str).str.lower().isin(("true", "1"))]
            # liquidity-ranked: the most tradeable pending names resolve first,
            # so a capped run buys the most useful information
            if "median_turnover_cr" in pend.columns:
                pend = pend.sort_values("median_turnover_cr", ascending=False)
            syms += pend["symbol"].tolist()
    return list(dict.fromkeys(syms))


def _refused(e: Exception) -> bool:
    """screener.in's rate limit, however fetch_company wrapped it."""
    return getattr(e, "code", None) == 429 or "429" in str(e)


def run(symbols: list[str], max_age_days: float, limit: int | None,
        sleep=time.sleep) -> pd.DataFrame:
    rows, failures, fetched = [], [], 0
    skipped_for_cap = 0
    refusals, wait, stopped = 0, 90, False
    t0 = time.time()
    for i, sym in enumerate(symbols, 1):
        data = load_company(sym)
        stale = data is not None and _age_days(data) > max_age_days
        # an empty parse cached by the pre-2026-07-25 consolidated-fallback bug
        # is not a cache hit — it is a blind spot that never heals on its own
        poisoned = data is not None and not has_real_data(data)
        if (data is None or stale or poisoned) and stopped:
            skipped_for_cap += 1
            if data is None or poisoned:
                continue
        elif data is None or stale or poisoned:
            if limit is not None and fetched >= limit:
                # SKIP, don't stop: names further down the list may already be
                # cached and cost nothing. The cap exists to bound NETWORK
                # calls (politeness), not to truncate the output.
                if not skipped_for_cap:
                    print(f"  fetch cap {limit} reached — remaining uncached names "
                          f"are skipped this run and picked up by the next",
                          flush=True)
                skipped_for_cap += 1
                continue
            fresh = None
            while fresh is None:
                try:
                    fresh = fetch_company(sym)
                except Exception as e:  # noqa: BLE001 — one dead page != dead run
                    if _refused(e) and refusals + 1 < MAX_REFUSALS:
                        refusals += 1
                        print(f"  [{i}/{len(symbols)}] 429 on {sym}; waiting {wait}s", flush=True)
                        sleep(wait)
                        wait = min(wait * 2, 900)
                        continue
                    if _refused(e):
                        stopped = True
                        print(f"  stopping live fetches: {MAX_REFUSALS} refusals in a row (HTTP 429); "
                              f"the next run picks up the rest", flush=True)
                    failures.append(sym)
                    if len(failures) <= 12:
                        print(f"  [{i}/{len(symbols)}] FAIL {sym}: {str(e)[:70]}", flush=True)
                    break
            if fresh is None:
                if data is None or poisoned:
                    continue
            else:
                data = fresh
                save_company(sym, data)
                fetched += 1
                refusals, wait = 0, 90
                sleep(PAUSE_SECONDS)
        try:
            rows.append({**flatten(sym, data), **penny_extras(data)})
        except Exception as e:  # noqa: BLE001 — parser drift on one page
            failures.append(sym)
            print(f"  [{i}/{len(symbols)}] PARSE FAIL {sym}: {str(e)[:60]}", flush=True)
        if i % 50 == 0:
            print(f"  [{i}/{len(symbols)}] fetched {fetched} live, "
                  f"{len(failures)} failures, {(time.time()-t0)/60:.1f} min", flush=True)

    df = pd.DataFrame(rows)
    if not df.empty:
        df.to_csv(OUT, index=False)
    print(f"\n{len(df)} rows -> {OUT}")
    print(f"live fetches: {fetched} | failures: {len(failures)} | "
          f"skipped (fetch cap): {skipped_for_cap} | {(time.time()-t0)/60:.1f} min")
    if failures:
        print(f"failed symbols (no screener.in page under that code): "
              f"{failures[:15]}{' ...' if len(failures) > 15 else ''}")
    return df


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("symbols", nargs="*")
    ap.add_argument("--max-age-days", type=float, default=14.0)
    ap.add_argument("--limit", type=int, default=None,
                    help="cap live fetches this run (cache hits are free)")
    ap.add_argument("--pending-only", action="store_true",
                    help="only the names held pending a market-cap read")
    args = ap.parse_args()

    syms = args.symbols or target_symbols(args.pending_only)
    if not syms:
        print("no penny universe yet — run scripts/build_penny_universe.py first")
        return
    print(f"penny fundamentals: {len(syms)} symbols "
          f"(pause {PAUSE_SECONDS}s, max age {args.max_age_days}d)", flush=True)
    run(syms, args.max_age_days, args.limit)


if __name__ == "__main__":
    main()
