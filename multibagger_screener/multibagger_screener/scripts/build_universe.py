"""
scripts/build_universe.py — Pipeline Step 1: download the official index
constituent lists (Nifty Smallcap 250 + Midcap 150 + Microcap 250), merge,
dedupe, and write universe.csv (symbol, company, industry, index_source).

Why index constituents (brief section 2A): ~650 liquid, tradeable names, and
NSE's own membership lists — today's list is still survivor-only for backtest
purposes (Design Law #4), but historical constituent snapshots exist and can
be added later for a less biased universe.

    python scripts/build_universe.py
"""

from __future__ import annotations

import io
import os
import sys
import urllib.request

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/csv,*/*",
}

# multiple mirrors per index — niftyindices.com and NSE archives host the same file
INDEX_SOURCES = {
    "smallcap250": [
        "https://niftyindices.com/IndexConstituent/ind_niftysmallcap250list.csv",
        "https://www.niftyindices.com/IndexConstituent/ind_niftysmallcap250list.csv",
        "https://nsearchives.nseindia.com/content/indices/ind_niftysmallcap250list.csv",
    ],
    "midcap150": [
        "https://niftyindices.com/IndexConstituent/ind_niftymidcap150list.csv",
        "https://www.niftyindices.com/IndexConstituent/ind_niftymidcap150list.csv",
        "https://nsearchives.nseindia.com/content/indices/ind_niftymidcap150list.csv",
    ],
    "microcap250": [
        "https://niftyindices.com/IndexConstituent/ind_niftymicrocap250_list.csv",
        "https://www.niftyindices.com/IndexConstituent/ind_niftymicrocap250list.csv",
        "https://nsearchives.nseindia.com/content/indices/ind_niftymicrocap250_list.csv",
    ],
}


def fetch_csv(urls: list[str]) -> pd.DataFrame:
    last_err: Exception | None = None
    for url in urls:
        try:
            req = urllib.request.Request(url, headers=_UA)
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read().decode("utf-8-sig", "ignore")
            df = pd.read_csv(io.StringIO(raw))
            if len(df) > 10:
                return df
        except Exception as e:  # noqa: BLE001 — try the next mirror
            last_err = e
    raise RuntimeError(f"all mirrors failed, last error: {last_err}")


def main() -> None:
    frames = []
    for index_name, urls in INDEX_SOURCES.items():
        try:
            df = fetch_csv(urls)
        except Exception as e:  # noqa: BLE001
            print(f"[FAIL] {index_name}: {e}")
            continue
        df.columns = [c.strip().lower() for c in df.columns]
        sym_col = next((c for c in df.columns if "symbol" in c), None)
        name_col = next((c for c in df.columns if "company" in c), None)
        ind_col = next((c for c in df.columns if "industry" in c), None)
        if sym_col is None:
            print(f"[FAIL] {index_name}: no symbol column in {list(df.columns)}")
            continue
        out = pd.DataFrame({
            "symbol": df[sym_col].astype(str).str.strip(),
            "company": df[name_col].astype(str).str.strip() if name_col else "",
            "industry": df[ind_col].astype(str).str.strip() if ind_col else "",
            "index_source": index_name,
        })
        frames.append(out)
        print(f"[ok]   {index_name}: {len(out)} names")

    if not frames:
        print("No index lists could be downloaded.")
        sys.exit(1)

    universe = pd.concat(frames, ignore_index=True)
    universe = universe.drop_duplicates(subset="symbol").reset_index(drop=True)

    # DROP NSE PLACEHOLDER SHELLS (2026-08-18). NSE publishes DUMMY-prefixed
    # rows in the constituent files as corporate-action placeholders (demerger
    # /scheme shells, e.g. DUMMYINXGN, DUMMYTRVN). They are not securities:
    # they never trade, so Yahoo has no series for them and update_prices
    # counts them as failures forever. That printed a permanent
    # "PRICE UPDATE FAILED for 2/654 symbols" health line into every night's
    # Telegram — an alarm that could never clear, which is how a real feed
    # outage gets ignored. Filtered here, at the source, rather than in
    # universe.csv (the weekly refresh rewrites that file).
    placeholders = universe["symbol"].str.upper().str.startswith("DUMMY")
    if placeholders.any():
        print(f"dropped {int(placeholders.sum())} NSE placeholder(s): "
              f"{universe.loc[placeholders, 'symbol'].tolist()}")
        universe = universe.loc[~placeholders].reset_index(drop=True)

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # THE COVERAGE-GAP COHORT (2026-09-07, PREREG_2026-09-07.md). Merged from a
    # COMMITTED file, never rebuilt here: scripts/build_gap_universe.py derives
    # it and is run deliberately at review. A pre-registered forward test cannot
    # measure a moving target, so weekly membership churn is exactly what must
    # not happen — and a live index fetch failing must never silently redefine
    # the cohort either.
    #
    # Index names WIN on collision (drop_duplicates keeps the first frame): if a
    # gap name is promoted into Microcap250 at the next rebalance it must be
    # labelled by its index, not left tagged nse_gap, or the forward record
    # would credit the experiment with an index name's trades.
    gap_path = os.path.join(root, "gap_universe.csv")
    if os.path.exists(gap_path):
        gap = pd.read_csv(gap_path)
        keep = [c for c in ("symbol", "company", "industry", "index_source")
                if c in gap.columns]
        gap = gap[keep]
        before = len(universe)
        universe = pd.concat([universe, gap], ignore_index=True)
        universe = universe.drop_duplicates(subset="symbol").reset_index(drop=True)
        promoted = len(gap) - (len(universe) - before)
        print(f"gap cohort: +{len(universe) - before} names from gap_universe.csv"
              + (f" ({promoted} already in an index — index label wins)" if promoted else ""))
    else:
        # Absent file = the cohort is not merged, and that is stated rather than
        # silently producing a 650-name universe that looks normal.
        print("NOTE: gap_universe.csv absent — coverage-gap cohort NOT included")

    out_path = os.path.join(root, "universe.csv")
    universe.to_csv(out_path, index=False)
    print(f"\nUniverse: {len(universe)} unique symbols -> {out_path}")
    print(universe["index_source"].value_counts().to_string())


if __name__ == "__main__":
    main()
