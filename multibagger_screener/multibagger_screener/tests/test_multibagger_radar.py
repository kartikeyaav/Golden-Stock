"""
The whole-market multibagger radar (scripts/multibagger_radar.py) on tiny
synthetic grids, plus its digest block. What must hold:
- a power play is found on the day it breaks out of its flag;
- a PERSISTENT state (an RS leader stays in the top 10% for months) is ONE
  event on the day it began — exactly what the research measured — not a
  fresh signal every day;
- the digest shows only signals that fired on the scan's own session.
"""

from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from research.grid import Grid  # noqa: E402
import multibagger_radar as MR  # noqa: E402
import send_telegram as ST  # noqa: E402


def _grid(close: np.ndarray) -> Grid:
    T, N = close.shape
    g = Grid(dates=pd.bdate_range("2024-01-01", periods=T), symbols=[f"S{i}" for i in range(N)],
             o=close.astype("float32"), h=(close * 1.01).astype("float32"),
             l=(close * 0.99).astype("float32"), c=close.astype("float32"),
             v=np.full((T, N), 1e6, "float32"), tv=np.full((T, N), 5e7, "float32"),
             dq=np.full((T, N), 5e5, "float32"), series=np.ones((T, N), "int8"))
    g.c_raw = g.c
    return g


def test_power_play_found_when_it_first_fires():
    """As registered and measured (H7): up 90%+ within 40 sessions, no pullback
    deeper than 25%, closing above the prior 25-session high — which fires on
    the surge itself, the first day the +90% condition is met."""
    T, N = 320, 30
    rng = np.random.default_rng(1)
    c = 100 * np.exp(np.cumsum(rng.normal(0, 0.004, (T, N)), axis=0))
    base = np.full(T, 100.0)
    base[300:] = np.linspace(100, 205, 20)            # +105% over the last 20 sessions
    c[:, 0] = base
    out = MR.scan(_grid(c))
    row = next(r for r in out["rows"] if r["sym"] == "S0")
    assert "H7" in row["signals"]


def test_an_old_power_play_is_not_repeated():
    """The same surge made new highs for days afterwards: still ONE event (the
    research dedupes to the first firing per 120 sessions)."""
    T, N = 320, 30
    rng = np.random.default_rng(2)
    c = 100 * np.exp(np.cumsum(rng.normal(0, 0.004, (T, N)), axis=0))
    base = np.full(T, 100.0)
    base[260:290] = np.linspace(100, 200, 30)         # the surge fired ~30 sessions ago
    base[290:] = np.linspace(200, 230, 30)            # a slow grind to new highs since
    c[:, 0] = base
    out = MR.scan(_grid(c))
    row = next((r for r in out["rows"] if r["sym"] == "S0"), None)
    assert row is None or "H7" not in row["signals"]


def test_a_persistent_rs_leader_is_one_event_not_a_daily_signal():
    T, N = 320, 40
    c = np.tile(np.linspace(100, 101, T)[:, None], (1, N))
    c[:, 0] = np.linspace(100, 400, T)                # the strongest name, all year
    out = MR.scan(_grid(c))
    row = next((r for r in out["rows"] if r["sym"] == "S0"), None)
    # it became a leader long before the last 10 sessions: no event on the radar now
    assert row is None or "H9" not in row["signals"]


def test_digest_shows_only_todays_radar_signals():
    radar = {"rows": [{"sym": "NEWONE", "signals": {"H7": "2026-09-25"}, "fresh": True, "ret_6m_pct": 140.0},
                      {"sym": "OLDONE", "signals": {"H9": "2026-09-18"}, "fresh": False, "ret_6m_pct": 90.0}]}
    raw = "# Daily scan — 2026-09-25 18:35\n\n"
    text = ST.build_digest(raw, public=True, radar=radar)
    assert "MULTIBAGGER RADAR" in text and "NEWONE — power play" in text and "OLDONE" not in text
    assert "MULTIBAGGER RADAR" not in ST.build_digest(raw, public=True, radar={"rows": []})
