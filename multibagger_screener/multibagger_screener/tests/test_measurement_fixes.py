"""
Guards for the four measurement defects AUDIT 2026-09-22 reproduced, fixed
2026-09-25. Each test was made to fail against the old behaviour first
(the legacy assertions below ARE that old behaviour, kept on purpose so the
opt-in nature of the engine fixes stays pinned).

  F3  an OPEN fill must be checked against its own bar's low
  F4  costs must be debited inside the ledger so equity is net
  F5  position management must replay missed sessions and fill gaps at the open
  F6  the last bar of a data cut is a week-end only on a Friday
"""

from __future__ import annotations

import os
import sys
import tempfile
from unittest.mock import patch

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

from backtest.engine import generate_signals, run_backtest, week_end_flags  # noqa: E402
import position_manager  # noqa: E402


def _flat(n=210, end="2026-09-22"):
    return pd.DataFrame(dict(date=pd.bdate_range(end=end, periods=n),
                             open=100., high=101., low=99., close=100., volume=100000.))


def _entry_frame():
    """Two bars: a signal row whose OPEN fill (100) is followed by a low of 80
    through a 90 stop, then a recovery."""
    df = _flat(2)
    df["fundamental_score"] = 1.0
    df["atr"] = 4.0
    df["avg_vol_50"] = 100000.0
    df["breakout_today"] = [True, False]
    df["is_week_end"] = False
    df["sma_50"] = 90.0
    df["sma_150"] = 90.0
    df.loc[0, "low"] = 80.0
    return df


# --- F3 ---------------------------------------------------------------------
def test_entry_day_stop_fires_for_open_fills():
    t, _ = run_backtest({"S": _entry_frame()}, entry_price_col="open",
                        stop_fill="gap_aware", size_on="equity", entry_day_stop=True)
    assert set(t["exit_reason"]) == {"stop_loss_entry_day"}, t["exit_reason"].tolist()
    assert (t["r_multiple"] == -1.0).all(), t["r_multiple"].tolist()


def test_entry_day_stop_is_opt_in_and_ignored_for_close_fills():
    legacy, _ = run_backtest({"S": _entry_frame()}, entry_price_col="open",
                             stop_fill="gap_aware", size_on="equity")
    assert set(legacy["exit_reason"]) == {"backtest_end"}      # the old behaviour, pinned
    closefill, _ = run_backtest({"S": _entry_frame()}, entry_price_col="close",
                                size_on="equity", entry_day_stop=True)
    # a close fill happened AFTER the bar's low, so the low cannot stop it out
    assert "stop_loss_entry_day" not in set(closefill["exit_reason"])


# --- F4 ---------------------------------------------------------------------
def test_cost_ledger_reconciles_to_net_equity():
    t, e = run_backtest({"S": _entry_frame()}, entry_price_col="open",
                        stop_fill="gap_aware", size_on="equity",
                        entry_day_stop=True, cost_pct_per_side=0.15)
    end_equity = float(e["equity"].iloc[-1])
    assert abs(end_equity - (1_000_000 + float(t["realized_pnl_net"].sum()))) < 0.01
    assert float(t["fees"].sum()) > 0
    assert (t["r_multiple_net"] < t["r_multiple"]).all()


def test_zero_cost_ledger_is_the_legacy_gross_ledger():
    a, ea = run_backtest({"S": _entry_frame()}, entry_price_col="open", size_on="equity")
    b, eb = run_backtest({"S": _entry_frame()}, entry_price_col="open", size_on="equity",
                         cost_pct_per_side=0.0)
    assert list(a.columns) == list(b.columns)          # no *_net columns at zero cost
    assert ea["equity"].tolist() == eb["equity"].tolist()


# --- F6 ---------------------------------------------------------------------
def test_last_bar_is_week_end_only_on_friday():
    tue = generate_signals(_flat(end="2026-09-22"), 1.0)      # Tuesday cut
    assert not bool(tue["is_week_end"].iloc[-1])
    fri = generate_signals(_flat(end="2026-09-18"), 1.0)      # Friday cut
    assert bool(fri["is_week_end"].iloc[-1])


def test_interior_week_ends_unchanged():
    d = pd.Series(pd.bdate_range("2026-01-01", "2026-03-31"))
    iso = d.dt.isocalendar()
    key = iso["year"].astype(int) * 100 + iso["week"].astype(int)
    old = (key != key.shift(-1)).fillna(True)
    new = week_end_flags(d)
    assert old.iloc[:-1].tolist() == new.iloc[:-1].tolist()


# --- F9 ---------------------------------------------------------------------
def test_unknown_regime_sizes_defensively():
    import scoring.regime as regime
    with patch.object(regime, "_breadth_scale", return_value=None), \
            patch.object(regime, "load_ohlcv", return_value=None):
        assert regime.market_risk_scale() == 0.5      # was 1.0: full risk on no data


def test_known_regimes_are_unchanged():
    import scoring.regime as regime
    with patch.object(regime, "_breadth_scale", return_value=1.0):
        assert regime.market_risk_scale() == 1.0
    with patch.object(regime, "_breadth_scale", return_value=0.5):
        assert regime.market_risk_scale() == 0.5


# --- F5 ---------------------------------------------------------------------
def _position(df, **over):
    row = dict(symbol="SYNTH", entry_date=str(df.date.iloc[-5].date()),
               entry_price=100., initial_stop=90., stop_current=90.,
               shares_trading=50, shares_core=50, trading_open=True, core_open=True,
               partial_taken=False, breakeven_moved=False, notes="synthetic")
    row.update(over)
    return row


def _run(df, row):
    with tempfile.TemporaryDirectory(prefix="golden_f5_") as tmp:
        pos = os.path.join(tmp, "positions.csv")
        led = os.path.join(tmp, "ledger.csv")
        pd.DataFrame([row]).to_csv(pos, index=False)
        with patch.object(position_manager, "load_ohlcv", return_value=df):
            alerts, _ = position_manager.check_positions(pos, led, "TEST")
        out = pd.read_csv(pos).to_dict("records")[0]
        ledger = pd.read_csv(led) if os.path.exists(led) else pd.DataFrame()
    return alerts, out, ledger


def test_missed_session_stop_is_replayed():
    df = _flat()
    df.loc[len(df) - 2, "low"] = 80.0            # breach on the session before the last
    stamp = str(df.date.iloc[-3].date())         # last checked before the breach
    alerts, out, ledger = _run(df, _position(df, last_checked=stamp))
    assert any("STOP HIT" in a for a in alerts), alerts
    assert not out["trading_open"] and not out["core_open"]
    assert str(ledger["date"].iloc[0]) == str(df.date.iloc[-2].date())


def test_gap_through_stop_fills_at_the_open():
    df = _flat()
    df.loc[len(df) - 1, ["open", "high", "low", "close"]] = [80., 85., 75., 82.]
    alerts, out, ledger = _run(df, _position(df))
    assert any("gapped through" in a for a in alerts), alerts
    assert float(ledger["price"].iloc[0]) == 80.0          # not the 90 stop


def test_unstamped_legacy_row_checks_only_the_latest_bar():
    df = _flat()
    df.loc[len(df) - 3, "low"] = 80.0            # an OLD breach the stamp-less row never saw
    alerts, out, _ = _run(df, _position(df))
    assert not any("STOP HIT" in a for a in alerts), alerts   # old behaviour for old rows
    assert out["last_checked"] == str(df.date.iloc[-1].date())


def test_rerun_on_the_same_bar_is_idempotent():
    df = _flat()
    df.loc[len(df) - 1, "high"] = 130.0          # partial level 125
    a1, out, _ = _run(df, _position(df, last_checked=str(df.date.iloc[-2].date())))
    assert any("PARTIAL" in a for a in a1)
    a2, _, _ = _run(df, {**out})
    assert a2 == []


def test_core_exit_ignores_a_week_that_closed_before_entry():
    df = _flat()
    df["close"] = 100.0
    df.loc[: len(df) - 8, "close"] = 100.0
    # every bar before the entry sits under a rising 150-DMA proxy: make the
    # MA high by putting a price spike early, then enter AFTER the last Friday
    df.loc[0:150, "close"] = 140.0
    row = _position(df, entry_date=str(df.date.iloc[-1].date()))
    alerts, out, _ = _run(df, row)
    assert not any("CORE LOT EXIT" in a for a in alerts), alerts
