"""
The momentum core (PREREG_2026-09-25_momentum_core.md) on synthetic prices.

Pins the registered timing and the properties that make a forward record
trustworthy: no rebalance before the first month-end on or after
registration; exactly one rebalance per closed month, at the NEXT session's
open; idempotent re-runs; NAV rebuilt from the recorded books; the breadth
rule halves exposure; and the ranking prefers steady strength over raw
volatility.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from unittest.mock import patch

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import momentum_core as M  # noqa: E402
from scoring import momentum  # noqa: E402


def _panel(end: str, n_days: int = 320, n_syms: int = 60, trend: bool = True):
    dates = pd.bdate_range(end=end, periods=n_days)
    rng = np.random.default_rng(7)
    cols = {}
    for i in range(n_syms):
        # every drift stays positive in a rising panel (0.0015 down to 0.0005),
        # still distinct per name so the ranking has something to rank
        drift = (0.0015 - i * (0.001 / n_syms)) if trend else -0.0012
        r = drift + rng.normal(0, 0.012, n_days)
        cols[f"S{i:02d}"] = 100 * np.exp(np.cumsum(r))
    C = pd.DataFrame(cols, index=dates)
    O = C.shift(1).fillna(C) * 1.001            # opens a touch above the prior close
    V = pd.DataFrame(1e6, index=dates, columns=C.columns)   # ~Rs 10 Cr a day: liquid
    return C, O, V


def _run_with(C, O, V, tmp, registered="2026-09-25"):
    with patch.object(M, "load_panels", return_value=(C, O, V)), \
            patch.object(M, "universe", return_value=list(C.columns)), \
            patch.object(M, "STATE", os.path.join(tmp, "state.json")), \
            patch.object(M, "LEDGER", os.path.join(tmp, "ledger.csv")), \
            patch.object(M, "REGISTERED", registered):
        return M.run()


def test_no_rebalance_before_the_first_month_end():
    C, O, V = _panel("2026-09-29")                # September not closed yet
    with tempfile.TemporaryDirectory() as tmp:
        st = _run_with(C, O, V, tmp)
        assert st["rebalances"] == [] and st["nav"] == []
        assert len(st["preview"]["targets"]) == momentum.TOP_N
        assert not os.path.exists(os.path.join(tmp, "ledger.csv"))


def test_one_rebalance_at_the_next_open_and_idempotent():
    C, O, V = _panel("2026-10-06")
    with tempfile.TemporaryDirectory() as tmp:
        st = _run_with(C, O, V, tmp)
        assert [r["signal"] for r in st["rebalances"]] == ["2026-09-30"]
        reb = st["rebalances"][0]
        assert reb["fill"] == "2026-10-01"
        assert len(reb["holdings_after"]) == momentum.TOP_N
        led = pd.read_csv(os.path.join(tmp, "ledger.csv"))
        assert set(led["action"]) == {"BUY"} and len(led) == momentum.TOP_N
        # fills are at the fill session's OPEN, never the signal close
        s = led["symbol"].iloc[0]
        assert abs(led["price"].iloc[0] - round(O.at[pd.Timestamp("2026-10-01"), s], 2)) < 0.01
        # a second run on the same data changes nothing
        st2 = _run_with(C, O, V, tmp)
        assert len(st2["rebalances"]) == 1
        assert len(pd.read_csv(os.path.join(tmp, "ledger.csv"))) == len(led)
        # NAV is rebuilt from the book for every session since the fill
        assert st2["nav"][0][0] == "2026-10-01" and st2["nav"][-1][0] == "2026-10-06"


def test_costs_come_out_of_the_book():
    C, O, V = _panel("2026-10-02")
    with tempfile.TemporaryDirectory() as tmp:
        st = _run_with(C, O, V, tmp)
        led = pd.read_csv(os.path.join(tmp, "ledger.csv"))
        assert abs(led["cost"].sum() - led["value"].sum() * M.COST_PCT / 100) < 1.0
        assert st["rebalances"][0]["cash_after"] >= 0


def test_breadth_below_half_halves_exposure():
    # 120 names with 320 bars: enough for breadth to be MEASURED (>=100 names
    # with >=300 bars), and every one of them falling, so breadth is ~0
    C, O, V = _panel("2026-10-06", n_syms=120, trend=False)
    with tempfile.TemporaryDirectory() as tmp:
        st = _run_with(C, O, V, tmp)
        reb = st["rebalances"][0]
        assert reb["breadth"] is not None and reb["breadth"] < 50
        assert reb["exposure"] == 0.5
        invested = sum(sh * O.at[pd.Timestamp(reb["fill"]), s] for s, sh in reb["holdings_after"].items())
        assert 0.45 < invested / M.CAPITAL < 0.52


def test_rising_market_is_fully_invested():
    C, O, V = _panel("2026-10-06", n_syms=120, trend=True)
    with tempfile.TemporaryDirectory() as tmp:
        reb = _run_with(C, O, V, tmp)["rebalances"][0]
        assert reb["breadth"] >= 50 and reb["exposure"] == 1.0


def test_unknown_breadth_is_defensive_not_full():
    # 60 names: too few to measure breadth. Missing data must not buy the
    # sleeve its maximum exposure (it did, before the test caught it).
    C, O, V = _panel("2026-10-06", n_syms=60, trend=True)
    with tempfile.TemporaryDirectory() as tmp:
        reb = _run_with(C, O, V, tmp)["rebalances"][0]
        assert reb["breadth"] is None and reb["exposure"] == 0.5


def test_holdings_inside_the_buffer_are_kept():
    ranked = pd.Series(np.linspace(3, -3, 60), index=[f"S{i:02d}" for i in range(60)])
    held = ["S30", "S45"]                          # rank 31 (kept) and 46 (dropped)
    t = momentum.target_names(ranked, held)
    assert "S30" in t and "S45" not in t and len(t) == momentum.TOP_N


def test_volatility_adjustment_prefers_steady_strength():
    dates = pd.bdate_range(end="2026-09-30", periods=300)
    rng = np.random.default_rng(1)
    cols = {"STEADY": 100 * np.exp(np.cumsum(0.002 + rng.normal(0, 0.005, 300))),
            "WILD": 100 * np.exp(np.cumsum(0.0022 + rng.normal(0, 0.05, 300)))}
    for i in range(45):
        cols[f"F{i:02d}"] = 100 * np.exp(np.cumsum(rng.normal(0, 0.01, 300)))
    C = pd.DataFrame(cols, index=dates)
    pp = momentum.panels(C, C * 1e6)
    ranked = momentum.score_at(pp, dates[-1])
    assert list(ranked.index).index("STEADY") < list(ranked.index).index("WILD")
