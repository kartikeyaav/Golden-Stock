"""
research/grid.py — the panel as aligned numpy grids, the point-in-time
universe, and the forward labels (PREREG_2026-09-26 §2).

Everything here is (sessions x companies) float32/bool. A value at row t uses
only rows <= t, except the labels, which are explicitly FORWARD and start at the
next session's open.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from data.nse_history import Panel, load_panel  # noqa: E402

CRORE = 1e7

# PREREG §2 — frozen
MIN_PRICE = 5.0
MIN_HISTORY = 250
MIN_MEDIAN_TURNOVER_CR = 1.0
TURNOVER_WINDOW = 60


def roll(a: np.ndarray, w: int, how: str, minp: int | None = None) -> np.ndarray:
    """Column-wise rolling statistic over the last `w` rows INCLUDING row t."""
    r = pd.DataFrame(a).rolling(w, min_periods=minp or w)
    out = getattr(r, how)()
    return out.to_numpy(dtype="float32")


def shift(a: np.ndarray, k: int) -> np.ndarray:
    """Row shift: shift(a, 1)[t] = a[t-1]; negative k looks forward."""
    out = np.full_like(a, np.nan, dtype="float32")
    if k > 0:
        out[k:] = a[:-k]
    elif k < 0:
        out[:k] = a[-k:]
    else:
        out[:] = a
    return out


def fwd_max(a: np.ndarray, k: int) -> np.ndarray:
    """max(a[t+1 .. t+k]) — strictly after t."""
    rev = pd.DataFrame(a[::-1]).rolling(k, min_periods=1).max().to_numpy(dtype="float32")[::-1]
    return shift(rev, -1)


def fwd_min(a: np.ndarray, k: int) -> np.ndarray:
    rev = pd.DataFrame(a[::-1]).rolling(k, min_periods=1).min().to_numpy(dtype="float32")[::-1]
    return shift(rev, -1)


def xrank(a: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Cross-sectional percentile rank (0..1] among universe members per row."""
    df = pd.DataFrame(np.where(mask, a, np.nan))
    return df.rank(axis=1, pct=True).to_numpy(dtype="float32")


@dataclass
class Grid:
    dates: pd.DatetimeIndex
    symbols: list[str]
    o: np.ndarray
    h: np.ndarray
    l: np.ndarray
    c: np.ndarray
    v: np.ndarray
    tv: np.ndarray          # traded value, rupees (unadjusted: value is value)
    dq: np.ndarray          # delivered quantity, adjusted like volume
    series: np.ndarray
    cache: dict = field(default_factory=dict)

    @property
    def T(self) -> int:
        return len(self.dates)

    @property
    def N(self) -> int:
        return len(self.symbols)

    # ---- cached derived grids --------------------------------------------
    def get(self, key: str, fn):
        if key not in self.cache:
            self.cache[key] = fn()
        return self.cache[key]

    def sma(self, w: int) -> np.ndarray:
        return self.get(f"sma{w}", lambda: roll(self.c, w, "mean"))

    def vavg(self, w: int) -> np.ndarray:
        """average volume over the w sessions BEFORE t (excludes t)."""
        return self.get(f"vavg{w}", lambda: shift(roll(self.v, w, "mean", minp=max(5, w // 2)), 1))

    def hmax_prior(self, w: int) -> np.ndarray:
        """max close over the w sessions before t (excludes t)."""
        return self.get(f"cmaxp{w}", lambda: shift(roll(self.c, w, "max", minp=w), 1))

    def ret(self, w: int) -> np.ndarray:
        return self.get(f"ret{w}", lambda: self.c / shift(self.c, w) - 1)

    def history(self) -> np.ndarray:
        """number of sessions with a close up to and including t."""
        return self.get("hist", lambda: np.cumsum(~np.isnan(self.c), axis=0).astype("int32"))

    def universe(self, min_turnover_cr: float = MIN_MEDIAN_TURNOVER_CR) -> np.ndarray:
        def _u():
            med = roll(self.tv, TURNOVER_WINDOW, "median", minp=TURNOVER_WINDOW // 2)
            raw_close = self.c_raw
            return ((~np.isnan(self.c)) & (raw_close >= MIN_PRICE)
                    & (self.history() >= MIN_HISTORY)
                    & (med >= min_turnover_cr * CRORE)
                    & np.isin(self.series, (1, 2, 3)))
        return self.get(f"U{min_turnover_cr}", _u)

    # ---- labels (FORWARD) --------------------------------------------------
    def entry(self) -> np.ndarray:
        """next session's open — the realistic fill for a signal at t's close."""
        return self.get("entry", lambda: shift(self.o, -1))

    def mb(self, mult: float, k: int) -> np.ndarray:
        def _mb():
            e = self.entry()
            m = fwd_max(self.c, k)
            out = np.where(np.isnan(e) | np.isnan(m), np.nan, (m >= mult * e).astype("float32"))
            # a label is only defined when the full window exists in the data
            out[self.T - k:] = np.nan
            return out.astype("float32")
        return self.get(f"mb{mult}_{k}", _mb)

    def fwd_ret(self, k: int) -> np.ndarray:
        """close at t+k (last traded close if the stock stopped trading —
        a delisted stock keeps its final price, it does not vanish) / entry."""
        def _fr():
            cf = pd.DataFrame(self.c).ffill().to_numpy(dtype="float32")
            out = shift(cf, -k) / self.entry() - 1
            out[self.T - k:] = np.nan
            return out
        return self.get(f"fr{k}", _fr)


def load_grid(start: str | None = None, path=None) -> Grid:
    p: Panel = Panel(path) if path else load_panel()
    rows = slice(None)
    if start:
        rows = p.dates >= pd.Timestamp(start)
    adj = p.adj[rows]
    g = Grid(dates=p.dates[rows], symbols=p.symbols,
             o=(p.open[rows] * adj), h=(p.high[rows] * adj), l=(p.low[rows] * adj),
             c=(p.close[rows] * adj), v=(p.volume[rows] / adj),
             tv=p.turnover[rows], dq=(p.deliv_qty[rows] / adj), series=p.series[rows])
    g.c_raw = p.close[rows]
    return g
