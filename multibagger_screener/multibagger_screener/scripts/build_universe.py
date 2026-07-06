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

    out_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "universe.csv")
    universe.to_csv(out_path, index=False)
    print(f"\nUniverse: {len(universe)} unique symbols -> {out_path}")
    print(universe["index_source"].value_counts().to_string())


if __name__ == "__main__":
    main()
