"""
research/fundamentals.py — point-in-time value/quality grids and H18-H20 of
PREREG_2026-09-26 (secondary: survivor-biased, see below).

Point in time: a fiscal year ending March Y is treated as KNOWN from 1 October Y
(six months after year end — Indian annual results are out by May for most
companies and by the AGM for the rest; the lag is deliberately conservative).

Definitions (annual, consolidated where screener.in has it):
  FCF            = cash from operations + cash from investing (investing flows
                   stand in for capex; acquisitions count against FCF)
  book           = equity capital + reserves
  market cap(t)  = market cap at fetch x adjusted close(t) / close at fetch
                   (the panel's adjustment makes splits/bonuses neutral; new
                   issuance is not modelled, so older market caps are
                   overstated for companies that raised equity since)
  FCF yield      = FCF / market cap;  B/M = book / market cap

SURVIVORSHIP. These pages exist for companies listed today. The share of the
point-in-time universe with no data is reported by coverage(); a signal can
only fire where data exist, so every H18-H20 result is conditional on having
survived to be fetched in 2026.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from research.grid import Grid, xrank
from research.fundamentals_fetch import OUT as FUND_DIR


def _series(tbl: dict, label: str) -> dict[int, float]:
    cols = (tbl or {}).get("columns") or []
    vals = ((tbl or {}).get("rows") or {}).get(label) or []
    out = {}
    for c, v in zip(cols, vals):
        c = str(c)
        if c.startswith("Mar ") and v is not None:
            try:
                out[int(c[4:])] = float(v)
            except ValueError:
                pass
    return out


def load_company(sym: str) -> dict | None:
    p = Path(FUND_DIR) / f"{sym}.json"
    if not p.exists():
        return None
    d = json.loads(p.read_text(encoding="utf-8"))
    pl, bs, cf = d.get("profit_loss"), d.get("balance_sheet"), d.get("cash_flow")
    sales = _series(pl, "Sales") or _series(pl, "Revenue")
    out = {
        "sales": sales,
        "op": _series(pl, "Operating Profit") or _series(pl, "Financing Profit"),
        "np": _series(pl, "Net Profit"),
        "cfo": _series(cf, "Cash from Operating Activity"),
        "cfi": _series(cf, "Cash from Investing Activity"),
        "eq": {y: _series(bs, "Equity Capital").get(y, np.nan) + _series(bs, "Reserves").get(y, np.nan)
               for y in _series(bs, "Equity Capital")},
        "assets": _series(bs, "Total Assets"),
        "mcap_now": (d.get("top_ratios") or {}).get("Market Cap"),
        "price_now": (d.get("top_ratios") or {}).get("Current Price"),
    }
    return out


def grids(g: Grid) -> dict[str, np.ndarray]:
    """T x N grids of fcf_yield, bm, and the turnaround / growth flags,
    NaN where the company has no data or the year is not yet known."""
    T, N = g.T, g.N
    fy = np.full((T, N), np.nan, "float32")
    bm = np.full((T, N), np.nan, "float32")
    turn = np.zeros((T, N), bool)
    inv_ok = np.zeros((T, N), bool)
    have = np.zeros(N, bool)
    dates = g.dates
    # the session index from which fiscal year Y is known (1 Oct Y)
    known_from = {y: int(np.searchsorted(dates.values, np.datetime64(f"{y}-10-01"))) for y in range(2005, 2031)}
    last_close = pd.DataFrame(g.c).ffill().iloc[-1].to_numpy()
    for j, sym in enumerate(g.symbols):
        f = load_company(sym)
        if not f or not f["mcap_now"] or not np.isfinite(last_close[j]) or last_close[j] <= 0:
            continue
        have[j] = True
        mc = f["mcap_now"] * g.c[:, j] / last_close[j]           # Rs crore, point in time
        years = sorted(set(f["sales"]) | set(f["eq"]))
        for k, y in enumerate(years):
            a = known_from.get(y)
            if a is None or a >= T:
                continue
            b = known_from.get(years[k + 1], T) if k + 1 < len(years) else T
            b = min(b, T)
            fcf = f["cfo"].get(y, np.nan) + f["cfi"].get(y, np.nan)
            e = f["eq"].get(y, np.nan)
            with np.errstate(divide="ignore", invalid="ignore"):
                fy[a:b, j] = fcf / mc[a:b]
                bm[a:b, j] = e / mc[a:b]
            np_hist = [f["np"].get(yy) for yy in (y - 2, y - 1, y)]
            if all(v is not None for v in np_hist):
                s0, s1 = f["sales"].get(y - 1), f["sales"].get(y)
                turn[a:b, j] = (np_hist[0] < 0 and np_hist[1] < 0 and np_hist[2] > 0
                                and s0 is not None and s1 is not None and s1 > s0)
            op0, op1 = f["op"].get(y - 1), f["op"].get(y)
            as0, as1 = f["assets"].get(y - 1), f["assets"].get(y)
            if None not in (op0, op1, as0, as1) and op0 and as0 and op0 > 0 and as0 > 0:
                inv_ok[a:b, j] = (as1 / as0 - 1) < (op1 / op0 - 1)
    return {"fcf_yield": fy, "bm": bm, "turnaround": turn, "invest_ok": inv_ok, "have": have}


def coverage(g: Grid, fg: dict, U: np.ndarray) -> dict:
    """Share of universe cells (and of the MB3_1y multibaggers) with data."""
    hasdata = np.isfinite(fg["bm"])
    by_year = {}
    for y in range(g.dates[0].year, g.dates[-1].year + 1):
        m = (g.dates.year == y)
        u = U[m]
        if u.sum():
            by_year[y] = round(float((hasdata[m] & u).sum() / u.sum()) * 100, 1)
    mb = g.mb(3.0, 252)
    mbm = (mb == 1) & U
    return {"universe_cells_with_data_pct_by_year": by_year,
            "mb3_events_with_data_pct": round(float((mbm & hasdata).sum() / max(mbm.sum(), 1)) * 100, 1),
            "companies_with_data": int(fg["have"].sum())}


def h18_cheap_cash_generative(g: Grid, fg: dict) -> np.ndarray:
    U = g.universe()
    cheap = (xrank(fg["fcf_yield"], U & np.isfinite(fg["fcf_yield"])) >= 0.70) & \
            (xrank(fg["bm"], U & np.isfinite(fg["bm"])) >= 0.70)
    weak = (xrank(g.ret(126), U) <= 0.5) & (xrank(g.ret(250), U) <= 0.5)
    return np.nan_to_num(cheap & weak & (fg["fcf_yield"] > 0)).astype(bool)


def h19_turnaround(g: Grid, fg: dict) -> np.ndarray:
    return fg["turnaround"]


def h20_cheap_new_uptrend(g: Grid, fg: dict, h2: np.ndarray, h5: np.ndarray) -> np.ndarray:
    U = g.universe()
    cheap = (xrank(fg["fcf_yield"], U & np.isfinite(fg["fcf_yield"])) >= 0.70) & \
            (xrank(fg["bm"], U & np.isfinite(fg["bm"])) >= 0.70)
    return np.nan_to_num(cheap & (fg["fcf_yield"] > 0) & (h2 | h5)).astype(bool)
