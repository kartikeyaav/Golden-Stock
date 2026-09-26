"""
research/sim.py on tiny synthetic grids where the right answer is known.

- a batch of next-open buys draws down ONE cash balance (no overspend);
- the -20% stop exits at the next session's open;
- a stock locked at its lower circuit (high == low, below the prior close)
  cannot be sold that day — the exit waits for a tradable session;
- the trend exit is not armed before `min_hold` sessions.
"""

from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from research.grid import Grid  # noqa: E402
from research.sim import SimConfig, run  # noqa: E402


def _grid(close: np.ndarray, high=None, low=None, open_=None, tv=1e12) -> Grid:
    T, N = close.shape
    dates = pd.bdate_range("2020-01-01", periods=T)
    # every session trades with a real range unless a test says otherwise
    o = close.copy() if open_ is None else open_
    h = close + 1.0 if high is None else high
    lo = close - 1.0 if low is None else low
    g = Grid(dates=dates, symbols=[f"S{i}" for i in range(N)], o=o.astype("float32"),
             h=h.astype("float32"), l=lo.astype("float32"), c=close.astype("float32"),
             v=np.full((T, N), 1e6, "float32"), tv=np.full((T, N), tv, "float32"),
             dq=np.full((T, N), 5e5, "float32"), series=np.ones((T, N), "int8"))
    g.c_raw = g.c
    return g


def test_batch_buys_share_one_cash_balance():
    T, N = 40, 4
    c = np.full((T, N), 100.0)
    g = _grid(c)
    sig = np.zeros((T, N), bool)
    sig[15, :] = True                                  # four names signal together
    cfg = SimConfig(max_positions=4, cost_pct=0.0, liq_cap=1.0, min_hold=1000)
    res = run(g, sig, None, cfg, start=g.dates[0])
    tr = res["trades"]
    assert len(tr) == 4
    spent = (tr["sh"] * tr["px"]).sum()
    assert spent <= cfg.start_cash + 1e-6            # never more than the cash that existed
    assert spent > 0.95 * cfg.start_cash              # and the slots were actually used
    assert abs(res["equity"].iloc[-1] - cfg.start_cash) < 1e3


def test_stop_exits_at_next_open():
    T = 30
    c = np.full((T, 1), 100.0)
    c[20:, 0] = 75.0                                   # -25% close on day 20 -> stop
    o = c.copy()
    o[21, 0] = 74.0
    g = _grid(c, open_=o)
    sig = np.zeros((T, 1), bool)
    sig[13, 0] = True                                  # buy at day 14's open = 100
    res = run(g, sig, None, SimConfig(max_positions=1, cost_pct=0.0, liq_cap=1.0), start=g.dates[0])
    t = res["trades"].iloc[0]
    assert t["entry_t"] == 14 and abs(t["px"] - 100.0) < 1e-6
    assert t["exit_t"] == 21 and abs(t["exit_px"] - 74.0) < 1e-6


def test_lower_circuit_lock_delays_the_exit():
    T = 30
    c = np.full((T, 1), 100.0)
    c[20:, 0] = 75.0                                   # stop decided at day 20's close
    c[21, 0] = 71.25                                   # day 21: locked limit-down
    c[22:, 0] = 70.0
    h, lo = c + 1.0, c - 1.0
    h[21, 0] = lo[21, 0] = 71.25                       # no range, below the prior close
    o = c.copy()
    o[21, 0] = 71.25
    o[22, 0] = 69.0
    g = _grid(c, high=h, low=lo, open_=o)
    sig = np.zeros((T, 1), bool)
    sig[13, 0] = True
    res = run(g, sig, None, SimConfig(max_positions=1, cost_pct=0.0, liq_cap=1.0), start=g.dates[0])
    t = res["trades"].iloc[0]
    assert t["exit_t"] == 22 and abs(t["exit_px"] - 69.0) < 1e-6


def test_trend_exit_waits_for_min_hold():
    T = 120
    c = np.linspace(100, 160, T)[:, None].astype(float)
    c[60, 0] = c[59, 0] * 0.9                           # one dip below the 50-day average
    g = _grid(c)
    sig = np.zeros((T, 1), bool)
    sig[55, 0] = True                                  # the dip lands 4 sessions after entry
    res = run(g, sig, None, SimConfig(max_positions=1, cost_pct=0.0, liq_cap=1.0, min_hold=20,
                                      stop_pct=0.5), start=g.dates[0])
    t = res["trades"].iloc[0]
    assert bool(t.get("open", False))                  # the early dip did not exit it
