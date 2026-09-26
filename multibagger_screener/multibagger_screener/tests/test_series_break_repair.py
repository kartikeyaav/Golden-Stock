"""
Breaks inside Yahoo's own series (scripts/update_prices.repair_scale_breaks).

Yahoo served MOTILALOFS with 1,240.8 on 2023-12-29 and 315.0 on 2024-01-01 —
its June-2024 bonus applied only back to the year boundary — and a refetch
returns the same break. The exchange's own closes arbitrate:
- NSE shows an ordinary day -> the jump is Yahoo's; the history BEFORE it is
  rescaled and later rows are untouched;
- NSE confirms a real action that day (restated prior close) -> kept;
- no exchange file -> left as is (never guessed).
"""

from __future__ import annotations

import os
import sys
from datetime import date

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import update_prices as UP  # noqa: E402


def _yahoo(n=30, brk=15, factor=0.25):
    dates = pd.bdate_range("2023-12-01", periods=n)
    close = np.linspace(1200, 1260, n)
    close[brk:] = close[brk:] * factor          # Yahoo's phantom cliff
    return pd.DataFrame({"date": dates, "open": close, "high": close * 1.01, "low": close * 0.99,
                         "close": close, "volume": 1000.0}), dates[brk - 1].date(), dates[brk].date()


def _exchange(sym, d0, d1, c0, c1, prev_close_d1=None):
    def rows(d):
        if d == d0:
            return pd.DataFrame({"symbol": [sym], "series": ["EQ"], "close": [c0], "prev_close": [c0]})
        if d == d1:
            return pd.DataFrame({"symbol": [sym], "series": ["EQ"], "close": [c1],
                                 "prev_close": [prev_close_d1 if prev_close_d1 is not None else c0]})
        return None
    return rows


def test_yahoo_only_break_is_repaired_and_later_rows_untouched():
    df, d0, d1 = _yahoo()
    y0, y1 = float(df["close"].iloc[14]), float(df["close"].iloc[15])
    # the exchange: an ordinary +0.5% session, no restatement
    fixed, notes = UP.repair_scale_breaks("MOSL", df, _exchange("MOSL", d0, d1, 1240.0, 1246.2),
                                          former=lambda s: [])
    assert any("rescaled" in n for n in notes)
    assert UP.scale_breaks(fixed) == []
    assert np.allclose(fixed["close"].iloc[15:], df["close"].iloc[15:])          # after: untouched
    step = fixed["close"].iloc[15] / fixed["close"].iloc[14]
    assert abs(step - 1246.2 / 1240.0) < 1e-6                                     # the exchange's move
    assert np.allclose(fixed["volume"].iloc[:15], 1000.0 / ((y1 / y0) / (1246.2 / 1240.0)))


def test_a_restated_corporate_action_is_adjusted_with_nse_ratio():
    """NSE restated the prior close on d1 (a 3:1 bonus: 1240 -> 310): the real
    move that day is close / restated base, and the history before is put on
    the new share basis — the fake -75% disappears."""
    df, d0, d1 = _yahoo()
    fixed, notes = UP.repair_scale_breaks("MOSL", df, _exchange("MOSL", d0, d1, 1240.0, 311.5,
                                                                prev_close_d1=310.0),
                                          former=lambda s: [])
    assert any("restated" in n and "rescaled" in n for n in notes)
    assert UP.scale_breaks(fixed) == []
    step = fixed["close"].iloc[15] / fixed["close"].iloc[14]
    assert abs(step - 311.5 / 310.0) < 1e-6


def test_a_genuine_crash_is_kept():
    df, d0, d1 = _yahoo(factor=0.44)
    # no restatement and 0.44 is no standard ratio within 3%: a real collapse
    fixed, notes = UP.repair_scale_breaks("YESB", df, _exchange("YESB", d0, d1, 1240.0, 545.6),
                                          former=lambda s: [])
    assert any("real move" in n for n in notes) and np.allclose(fixed["close"], df["close"])


def test_a_crash_near_a_standard_ratio_is_kept_when_volume_explodes():
    """0.5 IS a standard ratio (1:1 bonus) — but a 20x volume explosion is a
    crash, not a share-count change."""
    df, d0, d1 = _yahoo(factor=0.5)
    df.loc[15:, "volume"] = 20000.0
    fixed, notes = UP.repair_scale_breaks("CRASH", df, _exchange("CRASH", d0, d1, 1240.0, 620.0),
                                          former=lambda s: [])
    assert any("real move" in n for n in notes) and np.allclose(fixed["close"], df["close"])


def test_renamed_stock_is_found_under_its_former_symbol():
    df, d0, d1 = _yahoo()
    fixed, notes = UP.repair_scale_breaks("PATANJALI", df, _exchange("RUCHISOYA", d0, d1, 1240.0, 1246.2),
                                          former=lambda s: ["RUCHISOYA"])
    assert any("rescaled" in n for n in notes) and UP.scale_breaks(fixed) == []


def test_no_exchange_file_means_no_guess():
    df, _, _ = _yahoo()
    fixed, notes = UP.repair_scale_breaks("MOSL", df, lambda d: None, former=lambda s: [])
    assert np.allclose(fixed["close"], df["close"]) and "unavailable" in notes[0]


def test_clean_series_has_no_breaks():
    df, _, _ = _yahoo(factor=1.0)
    assert UP.scale_breaks(df) == []
