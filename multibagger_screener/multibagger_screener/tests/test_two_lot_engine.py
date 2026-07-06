"""
tests/test_two_lot_engine.py — verify the v2 two-lot engine against the same
hand-built synthetic series used to validate v1 (known-correct answers):

  WINNER: both lots enter on the breakout; trading lot books partial at +2.5R;
          core lot rides to the end and must out-earn the trading lot in R.
  LOSER : breakout immediately reverses -> BOTH lots stopped out ~-1R.
  FLAT  : never trades.

Run with: python -m tests.test_two_lot_engine
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np

from backtest.engine import generate_signals, run_backtest
from backtest.metrics import trade_stats, lot_breakdown, equity_stats
from tests.test_with_synthetic_data import make_winner_series, make_loser_series, make_flat_series


def main() -> None:
    np.random.seed(42)

    stocks = {
        "WINNER": make_winner_series(),
        "LOSER": make_loser_series(),
        "FLAT": make_flat_series(),
    }
    fundamental_scores = {"WINNER": 0.75, "LOSER": 0.70, "FLAT": 0.80}
    signals = {n: generate_signals(df, fundamental_scores[n]) for n, df in stocks.items()}

    trades_df, equity_df = run_backtest(signals, min_fundamental_score=0.55,
                                        starting_cash=1_000_000)

    print("=" * 70)
    print("TRADE LOG (one row per lot)")
    print("=" * 70)
    print(trades_df.to_string(index=False) if not trades_df.empty else "no trades")

    print()
    print("=" * 70)
    print("PER-LOT BREAKDOWN")
    print("=" * 70)
    for lot, stats in lot_breakdown(trades_df).items():
        print(f"{lot}: {stats}")
    print("blended:", trade_stats(trades_df))
    print("equity :", equity_stats(equity_df, starting_cash=1_000_000))

    # ---- assertions ----
    assert not trades_df.empty, "expected trades"
    assert "lot" in trades_df.columns, "trades_df must carry the lot column"

    flat = trades_df[trades_df["name"] == "FLAT"]
    assert flat.empty, "FLAT must never trade"

    loser = trades_df[trades_df["name"] == "LOSER"]
    assert not loser.empty, "LOSER should have entered on its breakout"
    assert set(loser["exit_reason"]) == {"stop_loss"}, "LOSER lots must exit via stop"
    assert loser["r_multiple"].min() >= -1.05, "stop must cap loss near -1R"
    assert loser["r_multiple"].max() <= -0.95, "both LOSER lots should be full -1R losses"

    winner = trades_df[trades_df["name"] == "WINNER"]
    assert not winner.empty, "WINNER should have entered"
    w_lots = set(winner["lot"])
    assert w_lots == {"trading", "core"}, f"WINNER should have both lots, got {w_lots}"

    w_trading = winner[winner["lot"] == "trading"].iloc[0]
    w_core = winner[winner["lot"] == "core"].iloc[0]
    assert w_trading["r_multiple"] > 0, "trading lot should be profitable"
    assert w_core["r_multiple"] > 0, "core lot should be profitable"
    assert w_core["r_multiple"] >= w_trading["r_multiple"], (
        "in a persistent uptrend the core lot must out-earn the trading lot — "
        "that asymmetry is the entire point of the two-lot structure"
    )
    # the golden-stock claim: the core lot is the one allowed to run big
    assert w_core["r_multiple"] >= 3.0, (
        f"core lot should ride well past the partial level, got {w_core['r_multiple']}R"
    )

    print()
    print("ALL TWO-LOT ENGINE CHECKS PASSED.")
    print(f"  trading lot: {w_trading['r_multiple']}R ({w_trading['exit_reason']})")
    print(f"  core lot   : {w_core['r_multiple']}R ({w_core['exit_reason']})")


if __name__ == "__main__":
    main()
