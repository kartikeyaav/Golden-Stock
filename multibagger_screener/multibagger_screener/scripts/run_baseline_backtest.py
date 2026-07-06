"""
scripts/run_baseline_backtest.py — the Phase A acceptance gate.

Runs the TECHNICAL-ONLY system (trend template + VCP breakout entries,
two-lot management, ATR stops) across every cached universe symbol with a
NEUTRAL fundamental score (0.6 constant — the gate passes everything, which
is exactly what "technical-only baseline" means). Applies costs. Compares to
NIFTY50 buy-and-hold. Writes baseline_report.md + baseline_trades.csv +
baseline_equity.csv.

THIS NUMBER IS THE BAR (Design Law #3): every dimension added in Phase B/C
must beat it out-of-sample or its weight is 0.

HONESTY (Design Law #4): today's constituent list = survivors only, and
fills are idealized. Results are DIRECTIONAL. Failing this test kills the
strategy; passing it merely means "not yet dead".

    python scripts/run_baseline_backtest.py
"""

from __future__ import annotations

import os
import sys
import time

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backtest.engine import generate_signals, run_backtest
from backtest.metrics import (apply_costs, compare_to_benchmark, equity_stats,
                              lot_breakdown, trade_stats)
from data.cache import list_cached, load_ohlcv

MIN_ROWS = 300
NEUTRAL_FUNDAMENTAL = 0.6
STARTING_CASH = 1_000_000


def main() -> None:
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    universe = pd.read_csv(os.path.join(root, "universe.csv"))
    cached = set(list_cached())

    t0 = time.time()
    signals = {}
    skipped = 0
    for i, sym in enumerate(universe["symbol"], 1):
        if sym not in cached:
            skipped += 1
            continue
        df = load_ohlcv(sym)
        if df is None or len(df) < MIN_ROWS:
            skipped += 1
            continue
        signals[sym] = generate_signals(df, NEUTRAL_FUNDAMENTAL)
        if i % 50 == 0:
            print(f"  signals {i}/{len(universe)} ({time.time()-t0:.0f}s)", flush=True)

    print(f"signal generation: {len(signals)} stocks in {(time.time()-t0)/60:.1f} min "
          f"({skipped} skipped)", flush=True)

    t1 = time.time()
    trades_df, equity_df = run_backtest(signals, min_fundamental_score=0.55,
                                        starting_cash=STARTING_CASH)
    print(f"backtest loop: {(time.time()-t1)/60:.1f} min", flush=True)

    if trades_df.empty:
        print("NO TRADES GENERATED — investigate before drawing any conclusion.")
        sys.exit(1)

    trades_df = apply_costs(trades_df, cost_pct_per_side=0.15)
    n_trades = trades_df[["name", "entry_date"]].drop_duplicates().shape[0]

    raw = trade_stats(trades_df)
    net = trade_stats(trades_df, pnl_col="realized_pnl_after_costs",
                      r_col="r_multiple_after_costs")
    lots_net = lot_breakdown(trades_df, pnl_col="realized_pnl_after_costs",
                             r_col="r_multiple_after_costs")
    eq = equity_stats(equity_df, STARTING_CASH)

    bench = load_ohlcv("NIFTY50")
    vs_bench = compare_to_benchmark(equity_df, bench, STARTING_CASH) if bench is not None else {}

    trades_df.to_csv(os.path.join(root, "baseline_trades.csv"), index=False)
    equity_df.to_csv(os.path.join(root, "baseline_equity.csv"), index=False)

    lines = [
        "# Baseline backtest — technical-only, two-lot (Phase A acceptance)",
        "",
        f"- Universe: {len(signals)} cached index-constituent stocks, "
        f"{eq.get('start_date')} to {eq.get('end_date')} ({eq.get('years')} yrs)",
        f"- Distinct positions: {n_trades}  (lot rows: {len(trades_df)})",
        f"- Costs: 0.15% per side applied",
        "",
        "## Blended (after costs)",
        f"{net}",
        "",
        "## Per lot (after costs)",
    ]
    for lot, stats in lots_net.items():
        lines.append(f"- {lot}: {stats}")
    lines += [
        "",
        "## Equity",
        f"{eq}",
        "",
        "## Vs NIFTY50 buy-and-hold",
        f"{vs_bench}",
        "",
        "## Raw (pre-cost) blended",
        f"{raw}",
        "",
        "**Honesty caveats (Design Law #4):** survivor-only universe (today's",
        "constituents), idealized fills (close entries, exact-stop exits, no",
        "circuit freezes), static neutral fundamentals. DIRECTIONAL ONLY.",
    ]
    report = "\n".join(lines)
    with open(os.path.join(root, "baseline_report.md"), "w", encoding="utf-8") as f:
        f.write(report)

    print()
    print(report)


if __name__ == "__main__":
    main()
