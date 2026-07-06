"""
fundamentals_loader.py — ingest fundamental data exported from screener.in.

WHY SCREENER.IN: it's the one Indian data source that officially supports this
exact workflow. Their Premium plan (check current price at screener.in/premium)
lets you:
  1. Build a "screen" (saved query) with the exact ratios you want as columns
     — ROCE, ROE, sales growth 3yr, profit growth 3yr, debt/equity, promoter
     holding, pledged percentage, PEG, etc.
  2. Click "Export to Excel" on the screen results to get all matching
     companies with those columns in one file.
This is a sanctioned bulk-export feature (not scraping), so there's no ToS
question about using it programmatically once you've exported the file.

For promoter PLEDGE data specifically, screener's export is usually good
enough, but if you want the most current quarter-end figure straight from the
source, NSE and BSE both publish the shareholding pattern (which includes
pledge %) as a structured filing each quarter — see shareholding.py.

USAGE:
    1. On screener.in, build a screen with (at minimum) these query terms:
       Market Capitalization, Sales growth 3Years, Profit growth 3Years,
       ROCE, ROE, Debt to equity, Promoter holding, Pledged percentage,
       PEG Ratio, and a "listing date" or IPO-derived age if you track it
       separately (screener doesn't natively expose listing date as a
       filter column, so cross-reference with the universe.py step, which
       gets listing/IPO date from the Kite instrument master or NSE's IPO
       archive instead).
    2. Export to Excel/CSV.
    3. Point COLUMN_MAP below at whatever screener actually named your
       columns (their export headers sometimes include units/suffixes) and
       call load_fundamentals(path).
"""

from __future__ import annotations

import pandas as pd

# Map "our internal name" -> "column name likely to appear in a screener.in
# export". Screener lets you customize which ratios appear and in what order,
# so double check this against your actual export the first time and adjust.
COLUMN_MAP = {
    "name": "Name",
    "market_cap_cr": "Market Capitalization",
    "revenue_cagr_3y": "Sales growth 3Years",
    "pat_cagr_3y": "Profit growth 3Years",
    "roce": "ROCE",
    "roe": "ROE",
    "debt_to_equity": "Debt to equity",
    "interest_coverage": "Interest Coverage Ratio",
    "promoter_holding_pct": "Promoter holding",
    "promoter_pledge_pct": "Pledged percentage",
    "peg_ratio": "PEG Ratio",
    "receivable_days": "Debtor days",
    "price": "Current Price",
    "pe_ratio": "Price to Earning",
}

REQUIRED_INTERNAL_COLUMNS = [
    "name", "market_cap_cr", "revenue_cagr_3y", "pat_cagr_3y",
    "roce", "roe", "debt_to_equity", "promoter_holding_pct",
    "promoter_pledge_pct",
]


def load_fundamentals(path: str, column_map: dict | None = None) -> pd.DataFrame:
    """Load a screener.in export (csv or xlsx) into a normalized DataFrame."""
    column_map = column_map or COLUMN_MAP

    if path.lower().endswith((".xlsx", ".xls")):
        raw = pd.read_excel(path)
    else:
        raw = pd.read_csv(path)

    raw.columns = [c.strip() for c in raw.columns]

    reverse_map = {v: k for k, v in column_map.items()}
    df = raw.rename(columns=reverse_map)

    missing = [c for c in REQUIRED_INTERNAL_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(
            f"Export is missing expected columns after mapping: {missing}. "
            f"Check COLUMN_MAP against your actual screener.in export headers: "
            f"{list(raw.columns)}"
        )

    numeric_cols = [c for c in df.columns if c not in ("name",)]
    for col in numeric_cols:
        df[col] = pd.to_numeric(
            df[col].astype(str).str.replace(",", "").str.replace("%", "").str.strip(),
            errors="coerce",
        )

    # promoter_pledge_pct is often blank/NaN when there's no pledge at all
    df["promoter_pledge_pct"] = df["promoter_pledge_pct"].fillna(0.0)

    return df.dropna(subset=["market_cap_cr", "roce"]).reset_index(drop=True)


def flag_missing_data(df: pd.DataFrame) -> pd.DataFrame:
    """Return rows with any null in the required columns — inspect these
    manually before trusting the composite score, since a screener export
    quirk (renamed company, delisted ticker, new IPO with <3yr history) is a
    common source of silent bad scores otherwise."""
    return df[df[REQUIRED_INTERNAL_COLUMNS].isnull().any(axis=1)]
