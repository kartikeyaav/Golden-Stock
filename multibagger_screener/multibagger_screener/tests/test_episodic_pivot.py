"""
tests/test_episodic_pivot.py — regression for the EPISODIC PIVOT entry class
(EP matrix, adopted 2026-07-19) and the event-stop plan override.

Run directly (no pytest dependency, same as the other tests):
    python tests/test_episodic_pivot.py
"""

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import EPISODIC, RISK
from scoring.technical_score import compute_entry_plan, detect_episodic_pivot


def _frame(n=100):
    """Quiet 99-day tape, last bar is the candidate EP day."""
    dates = pd.date_range("2026-01-01", periods=n, freq="B")
    df = pd.DataFrame({
        "date": dates,
        "open": np.full(n, 100.0), "high": np.full(n, 101.0),
        "low": np.full(n, 99.0), "close": np.full(n, 100.0),
        "volume": np.full(n, 200_000.0),
    })
    return df


def _gap(df, gap=1.12, close=1.15, vol_mult=4.5):
    prev_close = df["close"].iloc[-2]
    avg = df["volume"].iloc[:-1].rolling(50).mean().iloc[-1]
    i = df.index[-1]
    df.loc[i, "open"] = prev_close * gap
    df.loc[i, "close"] = prev_close * close
    df.loc[i, "high"] = prev_close * (close + 0.01)
    df.loc[i, "low"] = prev_close * (gap - 0.015)
    df.loc[i, "volume"] = avg * vol_mult
    return df


def main():
    # 1. canonical EP fires with the right facts
    ep = detect_episodic_pivot(_gap(_frame()))
    assert ep is not None, "canonical EP must fire"
    assert ep["gap_pct"] == 12.0 and ep["vol_mult"] == 4.5, ep
    assert ep["stop_price"] <= ep["close"], ep
    print(f"1. canonical EP fires: {ep}")

    # 2. negative controls — each broken leg must kill the signal
    weak_vol = _gap(_frame(), vol_mult=2.0)
    assert detect_episodic_pivot(weak_vol) is None, "2x volume must not fire"
    small_gap = _gap(_frame(), gap=1.04, close=1.06)
    assert detect_episodic_pivot(small_gap) is None, "4% gap must not fire"
    faded = _gap(_frame())
    i = faded.index[-1]
    faded.loc[i, "close"] = faded.loc[i, "open"] * 0.99   # red candle
    assert detect_episodic_pivot(faded) is None, "faded gap must not fire"
    short_hist = _gap(_frame(EPISODIC.min_bars - 5))
    assert detect_episodic_pivot(short_hist) is None, "short history must not fire"
    penny = _gap(_frame())
    penny[["open", "high", "low", "close"]] *= 0.10       # below price floor
    assert detect_episodic_pivot(penny) is None, "penny stock must not fire"
    print("2. negative controls hold (volume/gap/fade/history/price floor)")

    # 3. stop floor: locked-gap day (low == close) widens to 0.75*ATR
    locked = _gap(_frame())
    i = locked.index[-1]
    locked.loc[i, "low"] = locked.loc[i, "close"]         # degenerate tight low
    ep3 = detect_episodic_pivot(locked)
    assert ep3 is not None
    assert ep3["stop_price"] < float(locked["close"].iloc[-1]), \
        "stop must sit below the close even on a locked gap"
    print(f"3. locked-gap stop floored below close: {ep3['stop_price']}")

    # 4. plan honours the event stop and the hard width cap
    plan = compute_entry_plan(115.0, atr=2.0, stop_price=110.5)
    assert plan["stop_loss_price"] == 110.5 and "EP-day" in plan["stop_basis"]
    wide = compute_entry_plan(100.0, atr=2.0, stop_price=80.0)
    assert wide.get("skip") is True, "20%-wide event stop must be skipped"
    legacy = compute_entry_plan(100.0, atr=2.0)
    assert legacy["stop_loss_price"] == 100.0 - RISK.atr_stop_mult * 2.0, \
        "legacy ATR path must be unchanged"
    print("4. plan override + width cap + legacy path OK")

    print("\nALL EPISODIC-PIVOT CHECKS PASSED.")


if __name__ == "__main__":
    main()
