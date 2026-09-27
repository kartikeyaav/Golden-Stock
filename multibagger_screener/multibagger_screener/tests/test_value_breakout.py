"""
Cheap + new uptrend (H20) and the fundamentals behind it, on synthetic data.
What must hold:
- fiscal year Y is used only from 1 October Y (point in time), and the year
  before stays in force until then;
- market cap scales from each company's own fetch date by the price path;
- the quality and earnings-acceleration flags compute as registered;
- the value sleeve buys a cheap company breaking out of a 2-year base and
  ignores an expensive one doing the same.
"""

from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from research import fundamentals as F  # noqa: E402
from research.grid import Grid  # noqa: E402
import multibagger_sleeve as MS  # noqa: E402


def _grid(close: np.ndarray, start="2023-01-02") -> Grid:
    T, N = close.shape
    g = Grid(dates=pd.bdate_range(start, periods=T), symbols=[f"S{i}" for i in range(N)],
             o=close.astype("float32"), h=(close * 1.01).astype("float32"), l=(close * 0.99).astype("float32"),
             c=close.astype("float32"), v=np.full((T, N), 1e6, "float32"), tv=np.full((T, N), 5e7, "float32"),
             dq=np.full((T, N), 5e5, "float32"), series=np.ones((T, N), "int8"))
    g.c_raw = g.c
    return g


def _row(sym, fy, cfo, cfi, eq, sales, npf, mcap=1000.0, price=100.0, fetched="2026-09-26"):
    return {"symbol": sym, "fy": fy, "cfo": cfo, "cfi": cfi, "eq": eq, "sales": sales, "np": npf,
            "mcap_now": mcap, "price_now": price, "fetched_at": fetched}


def test_fiscal_year_is_used_only_from_1_october_and_mcap_scales_by_price():
    T = 900
    c = np.full((T, 1), 100.0)
    c[:, 0] = np.linspace(50, 100, T)                   # the price doubles over the window
    g = _grid(c)
    tab = pd.DataFrame([_row("S0", 2024, 60, -10, 400, 900, 40, fetched=str(g.dates[-1].date())),
                        _row("S0", 2025, 90, -10, 500, 1000, 50, fetched=str(g.dates[-1].date()))])
    fg = F.grids_from_table(g, tab)
    d = g.dates
    before = int(np.searchsorted(d.values, np.datetime64("2025-09-30"), side="right")) - 1
    after = int(np.searchsorted(d.values, np.datetime64("2025-10-01")))
    # on 2025-09-30 FY2024 is in force (FCF 50); from 2025-10-01 FY2025 (FCF 80)
    mc_b = 1000.0 * c[before, 0] / c[-1, 0]
    mc_a = 1000.0 * c[after, 0] / c[-1, 0]
    assert abs(fg["fcf_yield"][before, 0] - 50 / mc_b) < 1e-4
    assert abs(fg["fcf_yield"][after, 0] - 80 / mc_a) < 1e-4
    assert abs(fg["bm"][after, 0] - 500 / mc_a) < 1e-4
    # before FY2024 is known (1 Oct 2024) there is nothing
    first = int(np.searchsorted(d.values, np.datetime64("2024-10-01")))
    assert np.isnan(fg["fcf_yield"][first - 1, 0]) and np.isfinite(fg["fcf_yield"][first, 0])


def test_quality_and_acceleration_flags():
    T = 300
    g = _grid(np.full((T, 3), 100.0), start="2025-06-02")
    tab = pd.DataFrame([
        # S0: quality and accelerating (profit 10 -> 12 -> 20)
        _row("S0", 2023, 5, -1, 50, 100, 10), _row("S0", 2024, 6, -1, 55, 110, 12), _row("S0", 2025, 9, -1, 60, 130, 20),
        # S1: profitable but shrinking sales -> not quality
        _row("S1", 2023, 5, -1, 50, 100, 10), _row("S1", 2024, 6, -1, 55, 110, 12), _row("S1", 2025, 9, -1, 60, 90, 13),
        # S2: a loss -> neither
        _row("S2", 2023, 5, -1, 50, 100, 10), _row("S2", 2024, 6, -1, 55, 110, 12), _row("S2", 2025, 9, -1, 60, 130, -3),
    ])
    fy = F.fy_grids(g, tab)
    t = g.T - 1                                          # after 1 Oct 2025: FY2025 in force
    Q, A = F.quality(fy), F.earnings_acceleration(fy)
    assert Q[t, 0] and not Q[t, 1] and not Q[t, 2]
    assert A[t, 0] and not A[t, 2]                       # 20/12 = +67% > 12/10 = +20%


def test_value_sleeve_buys_the_cheap_breakout_not_the_expensive_one(monkeypatch):
    T, N = 760, 120
    rng = np.random.default_rng(5)
    c = 100 * np.exp(np.cumsum(rng.normal(0.0006, 0.01, (T, N)), axis=0))
    base = np.full(T, 100.0)
    base[-6:] = np.linspace(104, 110, 6)                  # a 2-year base, broken in the last sessions
    c[:, 0] = base                                       # S0: cheap
    c[:, 1] = base                                       # S1: the same chart, expensive
    g = _grid(c, start="2023-10-02")
    fetched = str(g.dates[-1].date())
    rows = []
    for j in range(N):
        cheap = j == 0
        rich = j == 1
        for fy in (2023, 2024, 2025):
            cfo = 300 if cheap else (1 if rich else 20)
            eq = 3000 if cheap else (10 if rich else 300)
            rows.append(_row(f"S{j}", fy, cfo, -10, eq, 1000, 50, mcap=1000.0, fetched=fetched))
    tab = pd.DataFrame(rows)
    sig = MS.signal_for(g, "value_breakout", tab)
    t = g.T - 1
    fired = np.nonzero(sig[-6:].any(axis=0))[0]
    assert 0 in fired and 1 not in fired
    monkeypatch.setitem(MS.SPECS["value_breakout"], "registered", str(g.dates[-8].date()))
    st, rows_ = MS.advance(g, {"nav": [], "last_session": None, "book": None}, "value_breakout", table=tab)
    held = set(st["book"]["pos"]) | set(st["book"]["pending_buys"])
    assert "S0" in held and "S1" not in held
