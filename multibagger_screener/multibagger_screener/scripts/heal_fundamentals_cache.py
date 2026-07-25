"""
scripts/heal_fundamentals_cache.py — find and refetch fundamentals-cache
records that hold no actual financials.

WHY THIS EXISTS (audit 2026-07-25). `fetch_company` used to accept the
/consolidated/ page whenever the quarterly table had ROWS. A single-entity
filer — most banks, insurers and standalone-only companies — has a
/consolidated/ URL that renders the row labels with every data column empty.
The test passed, the standalone fallback never fired, and an empty parse was
written to cache as a valid record. Nothing ever retried it: the cache-age
check saw a fresh timestamp.

The damage is asymmetric and that is what makes it dangerous. A name with no
fundamentals does not score LOW — `build_vetoes` returns [] on no data, the
composite renormalizes over whatever blocks survive, and the name floats to
the TOP of the table. Measured at discovery: 52 of 651 main-universe names and
22 of 218 penny names, and those 22 held penny ranks 1, 2, 3, 4, 6, 8, 9, 12
and 13.

`fetch_company` now refuses to return a page with no data, and both fetchers
treat an empty cached record as a miss, so this heals on its own from here.
This script is the one-shot repair for records already on disk, and a cheap
audit to re-run whenever a page layout is suspected of drifting.

    python scripts/heal_fundamentals_cache.py --dry-run
    python scripts/heal_fundamentals_cache.py
    python scripts/heal_fundamentals_cache.py --limit 40
"""

from __future__ import annotations

import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.screener_fetch import (FUND_CACHE_DIR, fetch_company, has_real_data,
                                 load_company, save_company)

PAUSE_SECONDS = 1.8  # the project's standing politeness pause


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _watched() -> set[str]:
    """Symbols any scorer actually reads: the index universe + the penny
    universe. The cache also holds ETFs and delisted codes that have no
    screener.in company page at all — refetching those burns polite requests
    to relearn the same nothing every run."""
    import csv
    out: set[str] = set()
    for name in ("universe.csv", "penny_universe.csv"):
        path = os.path.join(ROOT, name)
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8") as f:
            out.update(r["symbol"] for r in csv.DictReader(f) if r.get("symbol"))
    return out


def poisoned_symbols(watched_only: bool = True) -> list[str]:
    """Every cached record that carries no financials, in filename order."""
    watched = _watched() if watched_only else None
    out = []
    for path in sorted(FUND_CACHE_DIR.glob("*.json")):
        sym = path.stem.replace("_AND_", "&")
        if watched is not None and sym not in watched:
            continue
        data = load_company(sym)
        if data is not None and not has_real_data(data):
            out.append(sym)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true",
                    help="list the empty records, fetch nothing")
    ap.add_argument("--limit", type=int, default=None,
                    help="bound the number of network calls this run")
    ap.add_argument("--all", action="store_true",
                    help="include cached codes outside both universes (ETFs, "
                         "delisted) — they have no company page and will fail")
    args = ap.parse_args()

    bad = poisoned_symbols(watched_only=not args.all)
    total = len(list(FUND_CACHE_DIR.glob("*.json")))
    scope = "cache-wide" if args.all else "within the watched universes"
    print(f"fundamentals cache: {total} records, {len(bad)} carry no "
          f"financials ({scope})")
    if not bad:
        print("nothing to heal.")
        return 0
    print(f"  {bad}")
    if args.dry_run:
        return 0

    todo = bad[: args.limit] if args.limit else bad
    print(f"\nrefetching {len(todo)} (pause {PAUSE_SECONDS}s)...", flush=True)
    healed, still_empty, failed = [], [], []
    t0 = time.time()
    for i, sym in enumerate(todo, 1):
        try:
            data = fetch_company(sym)
        except Exception as e:  # noqa: BLE001 — one dead page != dead run
            # fetch_company now RAISES rather than returning an empty parse,
            # so this branch is "genuinely has no readable page", not silence
            still_empty.append(sym) if "no financials parsed" in str(e) else failed.append(sym)
            print(f"  [{i}/{len(todo)}] {sym}: {str(e)[:80]}", flush=True)
            time.sleep(PAUSE_SECONDS)
            continue
        save_company(sym, data)
        healed.append(sym)
        mc = (data.get("top_ratios") or {}).get("Market Cap")
        cols = len((data.get("quarters") or {}).get("columns") or [])
        print(f"  [{i}/{len(todo)}] {sym}: OK via {data['source_url'].split('/')[-2]} "
              f"— mcap {mc}, {cols} quarters", flush=True)
        time.sleep(PAUSE_SECONDS)

    print(f"\nhealed {len(healed)} | genuinely empty {len(still_empty)} | "
          f"fetch errors {len(failed)} | {(time.time()-t0)/60:.1f} min")
    if still_empty:
        print(f"  no readable page: {still_empty}")
    if failed:
        print(f"  retry next run: {failed}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
