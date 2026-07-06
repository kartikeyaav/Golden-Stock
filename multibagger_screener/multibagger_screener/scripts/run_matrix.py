"""
scripts/run_matrix.py — the pre-registered marginal-value experiment
(Design Law #3). Every config below was declared BEFORE results were seen;
no post-hoc knob tuning belongs in this file.

Window: entries 2023-08-01 -> end of data (all PIT dimensions live from
~Aug 2023 given screener's ~12-quarter lookback). Same universe, same
engine, same costs for every config — only the fundamental treatment varies.

  A   technical-only              fund=0.6 const (gate passes everything)   BASELINE
  B1  PIT gate, fail-open         unknown passes; known < 0.55 blocked
  B2  PIT gate, fail-closed       unknown blocked too (only known-good trade)
  B3  PIT gate, fail-open, 0.50   gate-threshold sensitivity
  D   PIT as entry-ranking        same-day candidates ranked by fundamental
                                  score instead of breakout volume (fail-open)

Each config reports: blended + per-lot stats after costs, and a split by
entry cohort P1 (2023-08 -> 2025-01) vs P2 (2025-01 -> end) — the walk-
forward check: a config that only wins in P1 was fit to the bull phase.

    python scripts/run_matrix.py
"""

from __future__ import annotations

import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backtest.engine import generate_signals, run_backtest
from backtest.metrics import apply_costs, equity_stats, lot_breakdown, trade_stats
from data.cache import list_cached, load_ohlcv
from scoring.pit_fundamentals import PITFundamentals

WINDOW_START = pd.Timestamp("2023-08-01")
P1_END = pd.Timestamp("2025-01-01")
MIN_ROWS = 300
STARTING_CASH = 1_000_000
GATE_DEFAULT = 0.55


def build_signals() -> dict[str, pd.DataFrame]:
    """Signals computed ONCE with the PIT series attached (fail-open NaN);
    configs then rewrite the fundamental column cheaply."""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    universe = pd.read_csv(os.path.join(root, "universe.csv"))
    industry_by_sym = dict(zip(universe["symbol"], universe["industry"]))
    cached = set(list_cached())

    signals: dict[str, pd.DataFrame] = {}
    t0 = time.time()
    for i, sym in enumerate(universe["symbol"], 1):
        if sym not in cached:
            continue
        df = load_ohlcv(sym)
        if df is None or len(df) < MIN_ROWS:
            continue
        pit = PITFundamentals(sym, industry_by_sym.get(sym))
        series = pit.daily_score_series(df)
        fund = series if not series.empty else float("nan")
        sig = generate_signals(df, fund if isinstance(fund, pd.Series) else np.nan)
        # restrict entries to the window (signals outside are zeroed)
        sig.loc[sig["date"] < WINDOW_START, "breakout_today"] = False
        signals[sym] = sig
        if i % 100 == 0:
            print(f"  signals {i}/{len(universe)} ({time.time()-t0:.0f}s)", flush=True)
    print(f"signals ready: {len(signals)} stocks in {(time.time()-t0)/60:.1f} min", flush=True)
    return signals


def cohort_split(trades: pd.DataFrame) -> dict:
    """Walk-forward read: stats by entry cohort (after costs)."""
    out = {}
    for name, mask in [
        ("P1_2023-08_to_2025-01", trades["entry_date"] < P1_END),
        ("P2_2025-01_onward", trades["entry_date"] >= P1_END),
    ]:
        sub = trades[mask]
        s = trade_stats(sub, pnl_col="realized_pnl_after_costs",
                        r_col="r_multiple_after_costs") if not sub.empty else {"num_trades": 0}
        out[name] = {k: s.get(k) for k in
                     ("num_trades", "win_rate_pct", "payoff_ratio", "expectancy_r", "total_pnl")}
    return out


def run_config(name: str, signals: dict[str, pd.DataFrame], fund_mode: str,
               gate: float, rank_by: str) -> dict:
    sigs = {}
    for sym, df in signals.items():
        d = df.copy()
        if fund_mode == "const":
            d["fundamental_score"] = 0.6
        elif fund_mode == "fail_closed":
            d["fundamental_score"] = d["fundamental_score"].fillna(0.0)
        sigs[sym] = d

    trades, equity = run_backtest(sigs, min_fundamental_score=gate,
                                  starting_cash=STARTING_CASH, rank_by=rank_by)
    if trades.empty:
        return {"config": name, "error": "no trades"}
    trades = apply_costs(trades)
    blended = trade_stats(trades, pnl_col="realized_pnl_after_costs",
                          r_col="r_multiple_after_costs")
    lots = lot_breakdown(trades, pnl_col="realized_pnl_after_costs",
                         r_col="r_multiple_after_costs")
    eq = equity_stats(equity, STARTING_CASH)
    return {
        "config": name,
        "positions": trades[["name", "entry_date"]].drop_duplicates().shape[0],
        "blended": blended,
        "core_lot": lots.get("core", {}),
        "cohorts": cohort_split(trades),
        "cagr_pct": eq.get("cagr_pct"),
        "max_dd_pct": eq.get("max_drawdown_pct"),
    }


CONFIGS = [
    ("A_technical_baseline", "const", GATE_DEFAULT, "volume"),
    ("B1_pit_gate_failopen", "asis", GATE_DEFAULT, "volume"),
    ("B2_pit_gate_failclosed", "fail_closed", GATE_DEFAULT, "volume"),
    ("B3_pit_gate_050", "asis", 0.50, "volume"),
    ("D_pit_entry_ranking", "asis", GATE_DEFAULT, "fundamental"),
]


def main() -> None:
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    signals = build_signals()

    results = []
    for name, fund_mode, gate, rank_by in CONFIGS:
        t0 = time.time()
        r = run_config(name, signals, fund_mode, gate, rank_by)
        r["runtime_min"] = round((time.time() - t0) / 60, 1)
        results.append(r)
        b = r.get("blended", {})
        print(f"[{name}] positions={r.get('positions')} "
              f"expectancy={b.get('expectancy_r')}R win%={b.get('win_rate_pct')} "
              f"payoff={b.get('payoff_ratio')} cagr={r.get('cagr_pct')}% "
              f"dd={r.get('max_dd_pct')}%", flush=True)

    lines = ["# Marginal-value matrix — PIT fundamentals vs technical baseline",
             "", f"Window: entries {WINDOW_START.date()} onward; costs 0.15%/side; "
             f"walk-forward cohorts split at {P1_END.date()}.", ""]
    for r in results:
        lines.append(f"## {r['config']}")
        for k in ("positions", "cagr_pct", "max_dd_pct"):
            lines.append(f"- {k}: {r.get(k)}")
        lines.append(f"- blended: {r.get('blended')}")
        lines.append(f"- core lot: {r.get('core_lot')}")
        lines.append(f"- cohorts: {r.get('cohorts')}")
        lines.append("")
    lines += ["## Reading rules (pre-registered)",
              "- A config beats baseline only if expectancy improves in BOTH cohorts.",
              "- P1-only improvement = fit to the bull phase -> reject.",
              "- If B-variants trade far fewer positions, judge total P&L and",
              "  drawdown alongside expectancy (a gate that only removes trades",
              "  must remove BAD trades to earn its place).",
              "- Survivor-bias caveat applies to every row equally; comparisons",
              "  between configs are the point, absolute numbers are not."]
    out = os.path.join(root, "matrix_report.md")
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"\n-> {out}")


if __name__ == "__main__":
    main()
