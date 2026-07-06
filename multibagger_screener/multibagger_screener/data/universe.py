"""
universe.py — build the starting stock universe: micro/small/mid-cap,
listed roughly 2-6 years, liquid enough to actually trade.

Three inputs are merged here:
  1. Kite's instrument master (data/kite_client.py) -> tradeable NSE equities.
  2. A listing-date table you maintain (Kite's instrument master does not
     carry IPO/listing date). NSE's IPO archive and sites like Chittorgarh
     publish complete historical IPO listing-date tables; export one to CSV
     with at minimum columns: tradingsymbol, listing_date. Recently listed
     names should already be in your Kite instrument master automatically.
  3. Fundamentals (data/fundamentals_loader.py) -> market cap, for the
     market-cap band filter, since Kite doesn't carry market cap either.

Turnover/liquidity filtering uses actual historical volume x price from Kite,
computed elsewhere (this module just defines the threshold check) — see
scoring/technical_score.py for where average daily turnover gets computed
from the price history you fetch per candidate.
"""

from __future__ import annotations

from datetime import datetime

import pandas as pd

from config import UNIVERSE


def load_listing_dates(path: str) -> pd.DataFrame:
    """CSV with columns: tradingsymbol, listing_date (YYYY-MM-DD)."""
    df = pd.read_csv(path, parse_dates=["listing_date"])
    required = {"tradingsymbol", "listing_date"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns: {missing}")
    return df


def filter_by_listing_age(
    listing_df: pd.DataFrame,
    as_of: datetime | None = None,
    min_years: float | None = None,
    max_years: float | None = None,
) -> pd.DataFrame:
    as_of = as_of or datetime.today()
    min_years = UNIVERSE.listing_age_min_years if min_years is None else min_years
    max_years = UNIVERSE.listing_age_max_years if max_years is None else max_years

    age_years = (as_of - listing_df["listing_date"]).dt.days / 365.25
    mask = (age_years >= min_years) & (age_years <= max_years)
    out = listing_df.loc[mask].copy()
    out["listing_age_years"] = age_years[mask]
    return out.reset_index(drop=True)


def filter_by_market_cap(
    fundamentals_df: pd.DataFrame,
    min_cr: float | None = None,
    max_cr: float | None = None,
) -> pd.DataFrame:
    min_cr = UNIVERSE.market_cap_min_cr if min_cr is None else min_cr
    max_cr = UNIVERSE.market_cap_max_cr if max_cr is None else max_cr
    mask = fundamentals_df["market_cap_cr"].between(min_cr, max_cr)
    return fundamentals_df.loc[mask].reset_index(drop=True)


def filter_by_liquidity(
    turnover_df: pd.DataFrame,
    turnover_col: str = "avg_daily_turnover_cr",
    min_turnover_cr: float | None = None,
) -> pd.DataFrame:
    min_turnover_cr = UNIVERSE.min_avg_daily_turnover_cr if min_turnover_cr is None else min_turnover_cr
    return turnover_df.loc[turnover_df[turnover_col] >= min_turnover_cr].reset_index(drop=True)


def build_universe(
    listing_df: pd.DataFrame,
    fundamentals_df: pd.DataFrame,
    as_of: datetime | None = None,
) -> pd.DataFrame:
    """Intersect listing-age filter with market-cap filter on company name /
    tradingsymbol. Liquidity filtering happens later, once you've pulled
    price history per candidate (see scoring/technical_score.py), since
    turnover isn't available until then."""
    age_ok = filter_by_listing_age(listing_df, as_of=as_of)
    cap_ok = filter_by_market_cap(fundamentals_df)

    merged = cap_ok.merge(
        age_ok,
        left_on="name",
        right_on="tradingsymbol",
        how="inner",
        suffixes=("", "_listing"),
    )
    return merged.reset_index(drop=True)
