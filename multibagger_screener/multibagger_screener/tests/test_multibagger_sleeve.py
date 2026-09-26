"""
The multibagger sleeve (scripts/multibagger_sleeve.py) on a synthetic market.
What must hold:
- nothing is traded on or before the registration date;
- a qualifying RS leader is bought at the NEXT session's open and ledgered;
- a re-run over the same sessions is a no-op; a later night continues from
  the last processed session (a missed night is caught up, never repeated);
- when breadth breaks (< 50% of the universe above its 200-day average) the
  book is emptied at the next open.
"""

from __future__ import annotations

import copy
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from research.grid import Grid  # noqa: E402
import multibagger_sleeve as MS  # noqa: E402


def _market(T=330, N=120, end="2026-10-09", crash_from=None, seed=3):
    rng = np.random.default_rng(seed)
    c = 100 * np.exp(np.cumsum(rng.normal(0.0008, 0.01, (T, N)), axis=0))   # a rising market
    c[:, 0] = np.linspace(100, 600, T)                                      # the clear leader
    if crash_from is not None:
        c[crash_from:, :] *= np.linspace(1.0, 0.5, T - crash_from)[:, None]  # breadth breaks
    dates = pd.bdate_range(end=end, periods=T)
    g = Grid(dates=dates, symbols=[f"S{i}" for i in range(N)], o=c.astype("float32"),
             h=(c * 1.01).astype("float32"), l=(c * 0.99).astype("float32"), c=c.astype("float32"),
             v=np.full((T, N), 1e6, "float32"), tv=np.full((T, N), 5e7, "float32"),
             dq=np.full((T, N), 5e5, "float32"), series=np.ones((T, N), "int8"))
    g.c_raw = g.c
    return g


def _fresh():
    return {"registered": MS.REGISTERED, "nav": [], "last_session": None, "book": None}


def test_buys_only_after_registration_at_the_next_open_and_ledgers_them():
    g = _market()
    st, rows = MS.advance(g, _fresh())
    first_day = min(r["date"] for r in rows) if rows else None
    assert rows and first_day > MS.REGISTERED
    buys = [r for r in rows if r["action"] == "BUY"]
    assert buys and all(r["date"] > MS.REGISTERED for r in buys)
    # a fill is at an OPEN strictly after the first processed session (decided at a close)
    assert buys[0]["date"] > st["nav"][0][0]
    assert "S0" in {r["symbol"] for r in buys}                  # the leader is held
    assert all(d > MS.REGISTERED for d, _ in st["nav"])


def test_rerun_is_a_noop_and_a_later_night_continues():
    g = _market()
    st, rows = MS.advance(g, _fresh())
    st2, rows2 = MS.advance(g, copy.deepcopy(st))
    assert rows2 == [] and st2["nav"] == st["nav"]
    g_more = _market(T=335, end="2026-10-16")                      # five more sessions
    st3, rows3 = MS.advance(g_more, copy.deepcopy(st))
    assert len(st3["nav"]) == len(st["nav"]) + 5
    assert st3["last_session"] == "2026-10-16"


def test_breadth_break_empties_the_book():
    g = _market(T=330, crash_from=318, end="2026-10-09")
    st, rows = MS.advance(g, _fresh())
    # risk off by the end: nothing held, nothing pending to buy
    assert st["risk_on"] is False
    assert not st["book"]["pending_buys"]
    held = set(st["book"]["pos"])
    assert held <= set(st["book"]["pending_sells"])            # anything still held is on its way out
