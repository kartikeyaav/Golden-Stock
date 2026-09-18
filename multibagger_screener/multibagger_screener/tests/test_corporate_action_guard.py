"""test_corporate_action_guard.py — a split must not close a winning position.

`update_prices._adjustment_detected` catches a split/bonus and refetches the
FULL history, so the cached series silently moves onto the new scale. Nothing
carried that through to paper_positions.csv, which stores raw entry and stop
prices — and the first thing check_positions does is

    if row["low"] <= stop:

so after a 2:1 split the cached low halves, the stored stop does not, and the
position takes a PHANTOM STOP-OUT at a fabricated ~50% loss, booked into the
append-only ledger the capital gate reads. Splits happen most often in names
that have run, so the bug destroys winners specifically.

PGIL split 2:1 mid-trade on 2026-09-10 and proves the mechanism is real; it was
already closed, so only the post-hoc reading was wrong that time.

Run:  python -m pytest tests/test_corporate_action_guard.py -q
"""

from __future__ import annotations

import os
import sys

import pandas as pd
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import position_manager as PM  # noqa: E402

ENTRY_DATE = "2026-06-01"


def _prices(scale: float = 1.0, last_low: float = 950.0) -> pd.DataFrame:
    """250 sessions of a calm uptrend, everything multiplied by `scale`.

    scale=0.5 is what Yahoo hands back after a 2:1 split: the SAME history,
    re-expressed on the new scale, including the bar the position entered on."""
    dates = pd.bdate_range("2025-07-01", periods=250)
    base = pd.Series(range(250), dtype=float) * 0.4 + 960.0
    df = pd.DataFrame({
        "date": dates,
        "open": base, "high": base + 10.0, "low": base - 10.0, "close": base,
        "volume": 100000.0,
    })
    # pin the entry bar and the final bar so the assertions are exact
    ei = df.index[df["date"] == pd.Timestamp(ENTRY_DATE)][0]
    df.loc[ei, ["open", "high", "low", "close"]] = [995.0, 1010.0, 990.0, 1000.0]
    df.loc[df.index[-1], ["open", "high", "low", "close"]] = [
        last_low + 40, last_low + 60, last_low, last_low + 50]
    for c in ("open", "high", "low", "close"):
        df[c] = df[c] * scale
    return df


def _position(tmp_path) -> str:
    p = tmp_path / "paper_positions.csv"
    pd.DataFrame([{
        "symbol": "SPLITCO", "entry_date": ENTRY_DATE, "entry_price": 1000.0,
        "initial_stop": 900.0, "stop_current": 900.0,
        "shares_trading": 100, "shares_core": 100,
        "trading_open": True, "core_open": True,
        "partial_taken": False, "breakeven_moved": False,
        "notes": "test", "verdict_id": "", "verdict": "BUY",
        "conviction": "HIGH", "size_plan": "FULL PLAN", "cohort": "capped",
    }]).to_csv(p, index=False)
    return str(p)


@pytest.fixture
def book(tmp_path, monkeypatch):
    def _run(scale, last_low=950.0):
        monkeypatch.setattr(PM, "load_ohlcv",
                            lambda sym: _prices(scale, last_low).copy())
        path = _position(tmp_path)
        ledger = str(tmp_path / "ledger.csv")
        alerts, _ = PM.check_positions(path, ledger_path=ledger, label="TEST")
        out = pd.read_csv(path).iloc[0]
        led = pd.read_csv(ledger) if os.path.exists(ledger) else pd.DataFrame()
        return alerts, out, led
    return _run


def test_unsplit_position_is_untouched(book):
    """Control: no re-adjustment, so nothing is rescaled and nothing exits."""
    alerts, out, led = book(scale=1.0)
    assert out["entry_price"] == 1000.0
    assert out["stop_current"] == 900.0
    assert bool(out["trading_open"]) and bool(out["core_open"])
    assert not any("re-adjusted" in a for a in alerts)


def test_a_two_for_one_split_does_not_close_the_position(book):
    """THE BUG. Post-split low is 475; the stored stop is 900. Without the
    guard that reads as a stop hit and books a ~50% loss."""
    alerts, out, led = book(scale=0.5)
    assert bool(out["trading_open"]), "the split closed a live position"
    assert bool(out["core_open"])
    assert led.empty or "stop hit" not in set(led.get("reason", [])), \
        "a phantom stop-out was booked into the ledger"


def test_the_split_rescales_prices_and_shares_consistently(book):
    alerts, out, _ = book(scale=0.5)
    assert out["entry_price"] == pytest.approx(500.0)
    assert out["initial_stop"] == pytest.approx(450.0)
    assert out["stop_current"] == pytest.approx(450.0)
    assert int(out["shares_trading"]) == 200
    assert int(out["shares_core"]) == 200
    # position VALUE and risk are unchanged by the corporate action
    assert out["entry_price"] * out["shares_trading"] == pytest.approx(1000.0 * 100)
    assert any("re-adjusted" in a for a in alerts), "the rescale was silent"


def test_a_real_stop_still_fires_after_a_split(book):
    """The guard must not become a blanket exemption: on the NEW scale the
    stop is 450, so a low of 440 is a genuine breach and must still exit."""
    _, out, led = book(scale=0.5, last_low=880.0)   # 880*0.5 = 440 < 450
    assert not bool(out["trading_open"]) and not bool(out["core_open"])
    assert "stop hit" in set(led["reason"])


def test_an_absurd_factor_is_refused_not_guessed(book):
    """A 1000x discrepancy is a data fault, not a corporate action. Refuse and
    say so — do not manage a position we cannot price."""
    alerts, out, led = book(scale=0.001)
    assert out["entry_price"] == 1000.0, "a bad factor was applied anyway"
    assert bool(out["trading_open"]), "the position was closed on bad data"
    assert led.empty or "stop hit" not in set(led.get("reason", []))
    assert any("needs a human" in a for a in alerts)
