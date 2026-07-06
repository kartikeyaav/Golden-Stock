"""
tests/test_with_synthetic_data.py — sanity-check the scoring + backtest
engine against hand-constructed price series where we KNOW what the answer
should be, since this sandbox has no live market data access.

Three synthetic stocks:
  WINNER  - steady uptrend, then a textbook VCP (three shrinking pullbacks on
            falling volume), then a volume breakout. Should: pass the trend
            template, detect a valid VCP, trigger a breakout entry, and (given
            a continued uptrend afterward) hit the partial-profit target.
  LOSER   - passes the trend template and even breaks out, but immediately
            reverses. Should: enter, then get stopped out for a controlled
            ~1R loss (proving the stop-loss logic actually caps damage).
  FLAT    - sideways/choppy the whole time. Should: never pass the trend
            template, never enter.

Run with: python -m tests.test_with_synthetic_data
"""

from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

from backtest.engine import generate_signals, run_backtest
from backtest.metrics import trade_stats, equity_stats
from scoring.technical_score import evaluate_trend_template, add_moving_averages, evaluate_vcp


def _make_dates(n, start="2022-01-03"):
    return pd.bdate_range(start=start, periods=n)


WINNER_BREAKOUT_IDX = 420  # phase1 (380 days) + 2 contractions x 16 days (32) + 8-day filler


def make_winner_series(n=500) -> pd.DataFrame:
    dates = _make_dates(n)
    price = np.zeros(n)
    volume = np.zeros(n)
    price[0] = 100.0
    phase1_len = 380

    # Phase 1: steady uptrend to build the 200/150/50 DMA stack (days 0-380)
    for i in range(1, phase1_len):
        price[i] = price[i - 1] * (1 + 0.0025 + np.random.normal(0, 0.006))
    volume[:phase1_len] = np.random.normal(200_000, 20_000, phase1_len)

    # Phase 2: two shrinking contractions (days 380-412), volume drying up.
    # bounce=8% between contractions matters: it needs to clear the zigzag
    # threshold (see config.TECHNICAL.zigzag_threshold_pct) so each contraction
    # gets recognized as a distinct leg rather than blurring into one long
    # decline. Depths of 20% then 8% keep this within a realistic VCP range
    # (Minervini's first contraction is commonly 15-30%) while still shallow
    # and short enough that the 50-day MA has time to recover above the
    # 150/200-day MAs by the breakout — a real constraint the trend template
    # enforces and that got violated in an earlier, deeper/longer draft of
    # this synthetic series (worth remembering if you tune these numbers).
    base = price[phase1_len - 1]
    contraction_depths = [0.20, 0.08]
    bounce = 0.08
    leg_len = 8
    idx = phase1_len
    for depth in contraction_depths:
        peak = base * (1 + bounce)
        trough = peak * (1 - depth)
        leg = np.concatenate([np.linspace(base, peak, leg_len), np.linspace(peak, trough, leg_len)])
        price[idx: idx + len(leg)] = leg
        volume[idx: idx + len(leg)] = np.linspace(150_000, 50_000, len(leg))  # drying up
        idx += len(leg)
        base = trough

    # tight flat base right before breakout, volume drying up further
    while idx < WINNER_BREAKOUT_IDX:
        price[idx] = base * (1 + np.random.normal(0, 0.002))
        volume[idx] = np.random.normal(40_000, 4_000)
        idx += 1

    # Phase 3: breakout + continued uptrend
    pivot = price[:WINNER_BREAKOUT_IDX].max()
    for i in range(WINNER_BREAKOUT_IDX, n):
        if i == WINNER_BREAKOUT_IDX:
            price[i] = pivot * 1.03
            volume[i] = 350_000  # breakout volume spike
        else:
            price[i] = price[i - 1] * (1 + 0.006 + np.random.normal(0, 0.005))
            volume[i] = np.random.normal(150_000, 20_000)

    df = pd.DataFrame({
        "date": dates, "close": price,
        "open": price * 0.998, "high": price * 1.01, "low": price * 0.99,
        "volume": np.abs(volume).astype(int),
    })
    return df


def make_loser_series(n=500) -> pd.DataFrame:
    df = make_winner_series(n)  # same setup through the breakout day...
    # ...but sharply reverse for 15 days right after breakout
    breakout_idx = WINNER_BREAKOUT_IDX
    peak = df["close"].iloc[breakout_idx]
    for i in range(breakout_idx + 1, min(breakout_idx + 15, n)):
        df.loc[i, "close"] = peak * (1 - 0.012 * (i - breakout_idx))
        df.loc[i, "open"] = df.loc[i, "close"] * 1.002
        df.loc[i, "high"] = df.loc[i, "close"] * 1.01
        df.loc[i, "low"] = df.loc[i, "close"] * 0.98
    return df


def make_flat_series(n=500) -> pd.DataFrame:
    dates = _make_dates(n)
    price = 100 + np.cumsum(np.random.normal(0, 0.3, n))
    price = np.clip(price, 90, 110)
    df = pd.DataFrame({
        "date": dates, "close": price,
        "open": price * 0.999, "high": price * 1.005, "low": price * 0.995,
        "volume": np.random.normal(100_000, 10_000, n).astype(int),
    })
    return df


def main():
    np.random.seed(42)

    print("=" * 70)
    print("STEP 1: Trend template + VCP detection sanity checks")
    print("=" * 70)

    winner = make_winner_series()
    winner_ma = add_moving_averages(winner)
    tt = evaluate_trend_template(winner_ma)
    print(f"WINNER trend template passed (full series, i.e. well after breakout): {tt.passed}")
    vcp = evaluate_vcp(winner_ma.iloc[:WINNER_BREAKOUT_IDX + 1])
    print(f"WINNER VCP valid on breakout day: {vcp['valid']}  depths={vcp.get('depths_used')}")

    flat = make_flat_series()
    flat_ma = add_moving_averages(flat)
    tt_flat = evaluate_trend_template(flat_ma)
    print(f"FLAT trend template passed (should be False): {tt_flat.passed}")

    print()
    print("=" * 70)
    print("STEP 2: Full signal generation + backtest across all three stocks")
    print("=" * 70)

    stocks = {
        "WINNER": make_winner_series(),
        "LOSER": make_loser_series(),
        "FLAT": make_flat_series(),
    }
    fundamental_scores = {"WINNER": 0.75, "LOSER": 0.70, "FLAT": 0.80}  # FLAT has great fundamentals but bad chart

    signals = {name: generate_signals(df, fundamental_scores[name]) for name, df in stocks.items()}

    for name, sig in signals.items():
        n_breakouts = sig["breakout_today"].sum()
        n_trend_pass_days = sig["trend_template_passed"].sum()
        print(f"{name}: trend-template-pass days = {n_trend_pass_days}, breakout signals = {n_breakouts}")

    trades_df, equity_df = run_backtest(signals, min_fundamental_score=0.55, starting_cash=1_000_000)

    print()
    print("=" * 70)
    print("STEP 3: Trade log")
    print("=" * 70)
    if trades_df.empty:
        print("No trades were generated — check signal generation above.")
    else:
        print(trades_df.to_string(index=False))

    print()
    print("=" * 70)
    print("STEP 4: Performance metrics")
    print("=" * 70)
    print("Trade stats:", trade_stats(trades_df))
    print("Equity stats:", equity_stats(equity_df, starting_cash=1_000_000))

    # ---- assertions: this is the actual "does the engine work" check ----
    n_breakouts_winner = signals["WINNER"]["breakout_today"].sum()
    assert n_breakouts_winner > 0, "WINNER should have produced a breakout signal"
    assert signals["FLAT"]["trend_template_passed"].sum() == 0, "FLAT should NEVER pass the trend template"
    assert not trades_df.empty, "Expected at least one trade (WINNER and/or LOSER breakout)"
    winner_trades = trades_df[trades_df["name"] == "WINNER"]
    loser_trades = trades_df[trades_df["name"] == "LOSER"]
    if not winner_trades.empty:
        assert winner_trades["r_multiple"].sum() > 0, "WINNER trades should be net profitable"
    if not loser_trades.empty:
        assert loser_trades["exit_reason"].isin(["stop_loss"]).any(), "LOSER should have been stopped out"
        assert loser_trades["r_multiple"].min() >= -1.2, "Loss should be capped near -1R by the stop-loss"

    print()
    print("ALL SANITY CHECKS PASSED.")


if __name__ == "__main__":
    main()
