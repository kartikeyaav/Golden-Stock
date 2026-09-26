"""
The 3:10 PM breakout check (scripts/breakout_watch.py). Offline: synthetic
daily and 5-minute bars, no Yahoo, no Telegram.

What must hold:
- the volume pace projects from the MEASURED share of the day done by the
  latest bar, so 1.5x average volume at the close reads 1.5x at 15:10;
- above the pivot on pace -> BREAKING OUT; above it on short volume -> NOT a
  buy; more than 5% above -> extended, never presented as a buy;
- outside 15:00-15:27 IST (a late wake-up) it does nothing.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, time as dtime

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import breakout_watch as BW  # noqa: E402

DAY = datetime(2026, 9, 28, 15, 10)


def _daily(avg_vol=100_000, px=100.0, n=80):
    idx = pd.bdate_range(end="2026-09-25", periods=n)
    return pd.DataFrame({"Open": px, "High": px * 1.02, "Low": px * 0.98,
                         "Close": px, "Volume": float(avg_vol)}, index=idx)


def _bars(last_px, day_volume_at_close, upto=dtime(15, 5)):
    """5-minute bars from 09:15 to `upto` (bar start), volume spread so the
    cumulative share at the last bar's END matches the measured curve."""
    starts = pd.date_range("2026-09-28 09:15", f"2026-09-28 {upto.strftime('%H:%M')}", freq="5min")
    bar_end = (starts[-1] + pd.Timedelta(minutes=5)).time()
    done = BW.volume_share(bar_end) * day_volume_at_close
    vol = np.full(len(starts), done / len(starts))
    return pd.DataFrame({"Open": last_px, "High": last_px, "Low": last_px,
                         "Close": last_px, "Volume": vol}, index=starts)


def test_volume_curve_is_measured_and_monotonic():
    vals = [v for _, v in sorted(BW.VOLUME_CURVE.items())]
    assert all(v is not None for v in vals)
    assert vals == sorted(vals) and 0.6 < vals[0] < vals[-1] < 1.0
    # interpolation between two measured points
    mid = BW.volume_share(dtime(15, 7, 30))
    assert BW.VOLUME_CURVE["15:05"] < mid < BW.VOLUME_CURVE["15:10"]


def test_on_pace_breakout_is_confirmed():
    r = BW.assess("X", 100.0, _daily(), _bars(101.5, day_volume_at_close=180_000), DAY)
    assert r["confirmed"] and not r["extended"]
    assert abs(r["pace"] - 1.8) < 0.05          # 180k at the close / 100k average


def test_above_pivot_on_short_volume_is_not_a_buy():
    r = BW.assess("X", 100.0, _daily(), _bars(101.5, day_volume_at_close=90_000), DAY)
    assert r["above"] and not r["confirmed"]
    text = BW.message([r], "2026-09-25", 1, "Mon 28 Sep 15:10", "")
    assert "BREAKING OUT" not in text and "VOLUME SHORT" in text


def test_extended_is_never_presented_as_a_buy():
    r = BW.assess("X", 100.0, _daily(), _bars(107.0, day_volume_at_close=300_000), DAY)
    assert r["confirmed"] and r["extended"]
    text = BW.message([r], "2026-09-25", 1, "Mon 28 Sep 15:10", "")
    assert "BREAKING OUT" not in text and "do not chase" in text


def test_below_pivot_says_nothing_is_breaking_out():
    r = BW.assess("X", 100.0, _daily(), _bars(98.0, day_volume_at_close=300_000), DAY)
    assert not r["above"]
    text = BW.message([r], "2026-09-25", 7, "Mon 28 Sep 15:10", "")
    assert "No candidate is above its pivot (7 watched)" in text


def test_outside_the_window_it_does_nothing(monkeypatch, capsys):
    class _Late(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 9, 28, 17, 40)     # a wake-up hours after the close
    monkeypatch.setattr(BW, "datetime", _Late)
    monkeypatch.setattr(sys, "argv", ["breakout_watch.py"])
    called = []
    monkeypatch.setattr(BW, "load_candidates", lambda: called.append(1) or ({}, "", ""))
    assert BW.main() == 0
    assert not called and "nothing to do" in capsys.readouterr().out
