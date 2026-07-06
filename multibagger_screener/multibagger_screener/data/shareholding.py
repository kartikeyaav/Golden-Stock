"""
shareholding.py — track promoter holding % and pledge % *trend* over time.

A single snapshot of "promoter holding 45%, pledge 2%" tells you much less
than the trend does. A promoter quietly reducing stake or steadily increasing
pledge over 3-4 quarters is one of the more reliable early warning signs in
Indian small/mid-caps, well before it shows up in the price.

SOURCE: NSE and BSE both require quarterly shareholding pattern filings
(Regulation 31 of SEBI LODR). These are public and free:
  - NSE: https://www.nseindia.com/companies-listing/corporate-filings-shareholding-pattern
  - BSE: https://www.bseindia.com/corporates/shpganalysis.aspx
There's no clean public API for these; the practical path is to download the
quarterly CSV/XBRL for your shortlisted candidates (after the fundamental
screen has already cut your universe down to a manageable size — don't try to
do this for the full universe every quarter, it doesn't scale by hand) and
feed them through `load_quarterly_snapshot` below.

This module works entirely on data you supply — it does not fetch anything
itself, deliberately, since scraping the exchange sites directly is fragile
and against most reasonable use policies at any real scale.
"""

from __future__ import annotations

import pandas as pd


def load_quarterly_snapshot(path: str) -> pd.DataFrame:
    """Expects a CSV with columns: name, quarter (e.g. '2026Q1'),
    promoter_holding_pct, promoter_pledge_pct. One row per company per
    quarter. Build this by hand or by combining exchange filings quarter
    over quarter — see module docstring for sourcing."""
    df = pd.read_csv(path)
    required = {"name", "quarter", "promoter_holding_pct", "promoter_pledge_pct"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns: {missing}")
    return df.sort_values(["name", "quarter"]).reset_index(drop=True)


def compute_holding_trend(df: pd.DataFrame, lookback_quarters: int = 4) -> pd.DataFrame:
    """For each company, compute the change in promoter holding and pledge
    over the trailing `lookback_quarters`, plus a simple red-flag boolean.

    Returns one row per company with:
      holding_change_pct   -> positive = promoter increasing stake (good sign)
      pledge_change_pct    -> positive = pledge rising (bad sign)
      pledge_red_flag      -> True if pledge rose OR current pledge > 5%
      holding_red_flag     -> True if holding fell > 2 percentage points
    """
    results = []
    for name, group in df.groupby("name"):
        group = group.sort_values("quarter").tail(lookback_quarters)
        if len(group) < 2:
            continue
        first, last = group.iloc[0], group.iloc[-1]
        holding_change = last["promoter_holding_pct"] - first["promoter_holding_pct"]
        pledge_change = last["promoter_pledge_pct"] - first["promoter_pledge_pct"]
        results.append({
            "name": name,
            "current_promoter_holding_pct": last["promoter_holding_pct"],
            "current_promoter_pledge_pct": last["promoter_pledge_pct"],
            "holding_change_pct": holding_change,
            "pledge_change_pct": pledge_change,
            "pledge_red_flag": bool(pledge_change > 0 or last["promoter_pledge_pct"] > 5.0),
            "holding_red_flag": bool(holding_change < -2.0),
        })
    return pd.DataFrame(results)
