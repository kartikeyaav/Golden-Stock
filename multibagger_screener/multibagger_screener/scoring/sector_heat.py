"""
sector_heat.py — the price-derived slice of Phase C's theme dimension:
industry-level relative strength, computed point-in-time.

For each month-end, each industry's median 6-month return ratio vs NIFTY is
percentile-ranked across industries -> heat grid (month x industry, 0-100).
A stock's effective heat on date X uses the LAST COMPLETED month's grid row
(no look-ahead by construction — everything derives from prices before X).

Unlike filing-based fundamentals (rejected as an entry gate by matrix v1 —
45-day lags made them trail price), sector heat has zero publication lag,
so it gets its own test: config E in matrix v2.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from data.cache import load_ohlcv

RS_MONTHS = 6
MIN_STOCKS_PER_INDUSTRY = 3


def build_close_panel(symbols: list[str]) -> pd.DataFrame:
    """Aligned close-price panel (dates x symbols) from the local cache."""
    frames = {}
    for sym in symbols:
        df = load_ohlcv(sym)
        if df is None or len(df) < 150:
            continue
        frames[sym] = df.set_index("date")["close"]
    return pd.DataFrame(frames)


def build_heat_grid(universe: pd.DataFrame, bench_symbol: str = "NIFTY50") -> pd.DataFrame:
    """Heat grid: index = month-end dates, columns = industries, values =
    percentile (0-100) of the industry's median 6m RS ratio that month."""
    industry_by_sym = dict(zip(universe["symbol"], universe["industry"]))
    panel = build_close_panel(list(universe["symbol"]))
    bench = load_ohlcv(bench_symbol)
    if panel.empty or bench is None:
        return pd.DataFrame()

    monthly = panel.resample("ME").last()
    bench_m = bench.set_index("date")["close"].resample("ME").last()

    stock_ret = monthly / monthly.shift(RS_MONTHS) - 1
    bench_ret = (bench_m / bench_m.shift(RS_MONTHS) - 1).reindex(stock_ret.index)

    rs_ratio = (1 + stock_ret).div(1 + bench_ret, axis=0)

    rows = {}
    for month, row in rs_ratio.iterrows():
        by_industry: dict[str, list[float]] = {}
        for sym, val in row.dropna().items():
            ind = industry_by_sym.get(sym)
            if ind:
                by_industry.setdefault(ind, []).append(float(val))
        medians = {ind: float(np.median(v)) for ind, v in by_industry.items()
                   if len(v) >= MIN_STOCKS_PER_INDUSTRY}
        if len(medians) < 5:
            continue
        s = pd.Series(medians)
        rows[month] = s.rank(pct=True) * 100
    return pd.DataFrame(rows).T.sort_index()


def heat_series_for_stock(dates: pd.Series, industry: str | None,
                          grid: pd.DataFrame) -> pd.Series:
    """Per-date effective heat for one stock: last completed month's value.
    Unknown industry / missing grid month -> NaN (fail-open in the gate)."""
    if grid.empty or not industry or industry not in grid.columns:
        return pd.Series(np.nan, index=range(len(dates)))
    col = grid[industry]
    d = pd.to_datetime(dates)
    idx = col.index.searchsorted(d, side="left") - 1  # strictly before date
    vals = [col.iloc[i] if i >= 0 else np.nan for i in idx]
    return pd.Series(vals, index=range(len(dates)))
