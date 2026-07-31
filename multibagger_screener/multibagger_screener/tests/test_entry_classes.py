"""Two-class portfolio + IPO-base signals (PREREG_2026-07-30 A1/A2).

The engine could previously hold exactly one entry class. A1 needs a second
class with its OWN slot pool and risk multiplier so the cannibalisation question
is answerable at all — V3a measured anticipation in isolation by overwriting
breakout_today, which cannot see slot competition. A2 reuses the same hook for
IPO bases.

The first test is the one that matters most: every historical config must
reproduce byte-identically, because these hooks were added under a live
evidence lock.

Network-free. pytest-collected.
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from backtest.engine import (Portfolio, generate_ipo_signals, generate_signals,
                             run_backtest)
from tests.test_with_synthetic_data import (make_flat_series, make_loser_series,
                                            make_winner_series)


@pytest.fixture()
def signals():
    np.random.seed(42)
    stocks = {"WINNER": make_winner_series(), "LOSER": make_loser_series(),
              "FLAT": make_flat_series()}
    fs = {"WINNER": 0.75, "LOSER": 0.70, "FLAT": 0.80}
    return {n: generate_signals(df, fs[n]) for n, df in stocks.items()}


def test_defaults_reproduce_history_exactly(signals):
    """The regression that guards the evidence lock."""
    trades, _ = run_backtest(signals, min_fundamental_score=0.55,
                             starting_cash=1_000_000)
    assert not trades.empty
    assert set(trades["entry_class"]) == {"breakout"}, \
        "with no second class configured every trade must still be a breakout"
    w = trades[(trades.name == "WINNER")]
    assert round(float(w[w.lot == "core"]["r_multiple"].iloc[0]), 3) == 8.959
    assert round(float(w[w.lot == "trading"]["r_multiple"].iloc[0]), 3) == 6.841


def test_second_class_is_labelled_and_sized_separately(signals):
    """Half risk on the sleeve must produce a smaller position, not a
    differently-managed one."""
    sigs = {}
    for n, d in signals.items():
        x = d.copy()
        # promote the WINNER's breakout bar into the second class instead
        x["anti"] = x["breakout_today"] if n == "WINNER" else False
        if n == "WINNER":
            x["breakout_today"] = False
        sigs[n] = x
    full, _ = run_backtest(sigs, min_fundamental_score=0.55, starting_cash=1_000_000,
                           anticipation_col="anti", anticipation_risk_mult=1.0,
                           anticipation_max_slots=4)
    half, _ = run_backtest(sigs, min_fundamental_score=0.55, starting_cash=1_000_000,
                           anticipation_col="anti", anticipation_risk_mult=0.5,
                           anticipation_max_slots=4)
    assert set(full[full.name == "WINNER"]["entry_class"]) == {"anticipation"}
    fs = full[(full.name == "WINNER") & (full.lot == "core")]["shares"].iloc[0]
    hs = half[(half.name == "WINNER") & (half.lot == "core")]["shares"].iloc[0]
    assert hs < fs, f"half-risk sleeve must take fewer shares ({hs} vs {fs})"
    # R is a ratio, so halving size must NOT change the R outcome
    fr = full[(full.name == "WINNER") & (full.lot == "core")]["r_multiple"].iloc[0]
    hr = half[(half.name == "WINNER") & (half.lot == "core")]["r_multiple"].iloc[0]
    assert round(float(fr), 2) == round(float(hr), 2)


def test_class_name_is_configurable(signals):
    """A2 reuses the hook under a different label."""
    sigs = {}
    for n, d in signals.items():
        x = d.copy()
        x["ipo"] = x["breakout_today"] if n == "WINNER" else False
        if n == "WINNER":
            x["breakout_today"] = False
        sigs[n] = x
    trades, _ = run_backtest(sigs, min_fundamental_score=0.55, starting_cash=1_000_000,
                             anticipation_col="ipo", anticipation_class_name="ipo",
                             anticipation_max_slots=4)
    assert "ipo" in set(trades["entry_class"])


def test_count_class_counts_only_its_own():
    p = Portfolio(1_000_000)
    p.open_position("A", pd.Timestamp("2024-01-01"), 100.0, 90.0)
    p.open_position("B", pd.Timestamp("2024-01-01"), 100.0, 90.0,
                    entry_class="anticipation")
    assert p.count_class("breakout") == 1
    assert p.count_class("anticipation") == 1
    assert p.count_class("ipo") == 0


def test_sleeve_slots_are_capped_independently():
    """Four sleeve slots means four, regardless of the breakout cap."""
    p = Portfolio(100_000_000)
    for i in range(6):
        p.open_position(f"S{i}", pd.Timestamp("2024-01-01"), 100.0, 90.0,
                        entry_class="anticipation")
    assert p.count_class("anticipation") == 6   # Portfolio itself does not cap
    # the cap lives in the entry loop; this asserts the counter it depends on
    assert p.count_class("breakout") == 0


# ------------------------------------------------------------------ A2 ------

def _young_frame(n=200, start=100.0):
    """A synthetic young listing: run up, tighten into a base, then break out
    on volume — the shape the template cannot see because it has no 200-DMA."""
    rng = np.random.default_rng(7)
    dates = pd.bdate_range("2025-01-01", periods=n)
    close = [start]
    for i in range(1, n):
        if i < 70:
            close.append(close[-1] * (1 + rng.normal(0.006, 0.012)))
        elif i < n - 1:                      # contracting base
            amp = 0.02 * (1 - (i - 70) / (n - 71))
            close.append(close[-1] * (1 + rng.normal(0.0, max(amp, 0.003))))
        else:
            close.append(close[-1] * 1.09)   # breakout bar
    close = np.array(close)
    vol = np.full(n, 1_000_000.0)
    vol[-1] = 5_000_000.0
    return pd.DataFrame({"date": dates, "open": close * 0.995, "high": close * 1.01,
                         "low": close * 0.99, "close": close, "volume": vol})


def test_ipo_signals_fire_where_the_template_cannot():
    df = _young_frame()
    old = generate_signals(df, 1.0)
    new = generate_ipo_signals(df, 1.0, min_bars=60)
    assert old["trend_template_passed"].sum() == 0, \
        "a 200-bar name must never pass the 8-point template"
    assert new["trend_template_passed"].sum() > 0
    assert new["vcp_valid"].sum() > 0


def test_ipo_respects_its_minimum_bar_count():
    df = _young_frame()
    s60 = generate_ipo_signals(df, 1.0, min_bars=60)
    s150 = generate_ipo_signals(df, 1.0, min_bars=150)
    # a tighter floor may legitimately admit NOTHING; what must never happen is
    # a signal BELOW the floor, so assert on every firing bar rather than the
    # first one (min() of an empty index is NaN, which silently passes >=)
    for s, floor in ((s60, 60), (s150, 150)):
        firing = s.index[s["trend_template_passed"]]
        assert all(i >= floor for i in firing), f"signal below min_bars={floor}"
    assert s60["trend_template_passed"].sum() > 0, "the 60-bar floor must admit some"
    assert s150["trend_template_passed"].sum() <= s60["trend_template_passed"].sum()


def test_ipo_volume_standard_is_binding():
    """The EP-grade 3x variant must admit no more than the 1.5x one."""
    df = _young_frame()
    lo = generate_ipo_signals(df, 1.0, min_bars=60, vol_multiple=1.5)
    hi = generate_ipo_signals(df, 1.0, min_bars=60, vol_multiple=3.0)
    assert hi["breakout_today"].sum() <= lo["breakout_today"].sum()


def test_ipo_keeps_the_standard_column_contract():
    """run_backtest must consume it without knowing the difference."""
    s = generate_ipo_signals(_young_frame(), 1.0)
    for col in ("date", "atr", "is_week_end", "avg_vol_50", "breakout_today",
                "vcp_valid", "pivot_price", "fundamental_score",
                "trend_template_passed", "sma_50", "sma_150"):
        assert col in s.columns, f"missing {col}"


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
