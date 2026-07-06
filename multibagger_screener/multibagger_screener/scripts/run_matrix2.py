"""
scripts/run_matrix2.py — matrix v2, pre-registered before results are seen.

Follows v1's verdict (PIT fundamentals REJECTED as entry gate/ranking).
v2 tests what fundamentals and themes might still earn, plus execution
robustness of the surviving baseline:

  A     technical baseline (re-run; trades saved for forensics)
  E40   sector-heat gate: entries only when industry heat pctile >= 40
        (price-derived, zero publication lag — v1's rejection doesn't apply)
  E60   sector-heat gate at 60 (dose-response check)
  F1    core-lot PATIENCE: strong PIT fundamentals (>=0.60) allow one extra
        weekly close below the 30-week MA before the core exits
        ("fundamentals earn patience on the HOLD, not the entry")
  F2    fundamentals-modulated lot split (strong -> 60% core, weak -> 30%)
  S1    stress: entries fill at NEXT day's open (not breakout close)
  S3    stress: stops fill gap-aware (at the open when gapped through)
  S2    stress: A's trades re-costed at 0.40%/side (derived, no re-run)

Reading rules (pre-registered):
  - E judged like v1: must improve expectancy in BOTH cohorts.
  - F1/F2 judged primarily on CORE-LOT stats (that's what they modulate);
    blended must not degrade materially.
  - S1/S2/S3 judge the BASELINE's fragility: A must remain clearly positive
    (expectancy > +0.5R) under every stress or the edge is fill-dependent.

    python scripts/run_matrix2.py
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
from scoring.sector_heat import build_heat_grid, heat_series_for_stock

WINDOW_START = pd.Timestamp("2023-08-01")
P1_END = pd.Timestamp("2025-01-01")
MIN_ROWS = 300
STARTING_CASH = 1_000_000
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRADES_DIR = os.path.join(ROOT, "matrix_trades")


def build_signals() -> tuple[dict[str, pd.DataFrame], pd.DataFrame]:
    universe = pd.read_csv(os.path.join(ROOT, "universe.csv"))
    industry_by_sym = dict(zip(universe["symbol"], universe["industry"]))
    cached = set(list_cached())

    print("building sector heat grid...", flush=True)
    grid = build_heat_grid(universe)
    print(f"heat grid: {grid.shape[0]} months x {grid.shape[1]} industries", flush=True)

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
        sig = generate_signals(df, series if not series.empty else np.nan)
        sig.loc[sig["date"] < WINDOW_START, "breakout_today"] = False
        sig["sector_heat"] = heat_series_for_stock(
            sig["date"], industry_by_sym.get(sym), grid).to_numpy()
        signals[sym] = sig
        if i % 100 == 0:
            print(f"  signals {i}/{len(universe)} ({time.time()-t0:.0f}s)", flush=True)
    print(f"signals ready: {len(signals)} stocks in {(time.time()-t0)/60:.1f} min", flush=True)
    return signals, grid


def prep(signals, heat_gate: float | None = None, shift_entry: bool = False):
    out = {}
    for sym, df in signals.items():
        d = df.copy()
        if heat_gate is not None:
            known_cold = d["sector_heat"].notna() & (d["sector_heat"] < heat_gate)
            d.loc[known_cold, "breakout_today"] = False  # NaN heat = fail-open
        if shift_entry:
            d["breakout_today"] = d["breakout_today"].shift(1, fill_value=False)
        out[sym] = d
    return out


def cohort_split(trades: pd.DataFrame) -> dict:
    out = {}
    for name, mask in [("P1", trades["entry_date"] < P1_END),
                       ("P2", trades["entry_date"] >= P1_END)]:
        sub = trades[mask]
        s = trade_stats(sub, pnl_col="realized_pnl_after_costs",
                        r_col="r_multiple_after_costs") if not sub.empty else {"num_trades": 0}
        out[name] = {k: s.get(k) for k in
                     ("num_trades", "win_rate_pct", "payoff_ratio", "expectancy_r", "total_pnl")}
    return out


def summarize(name: str, trades: pd.DataFrame, equity: pd.DataFrame,
              cost_pct: float = 0.15) -> dict:
    trades = apply_costs(trades, cost_pct_per_side=cost_pct)
    os.makedirs(TRADES_DIR, exist_ok=True)
    trades.to_csv(os.path.join(TRADES_DIR, f"{name}.csv"), index=False)
    eq_window = equity[equity["date"] >= WINDOW_START]
    return {
        "config": name,
        "positions": trades[["name", "entry_date"]].drop_duplicates().shape[0],
        "blended": trade_stats(trades, pnl_col="realized_pnl_after_costs",
                               r_col="r_multiple_after_costs"),
        "core_lot": lot_breakdown(trades, pnl_col="realized_pnl_after_costs",
                                  r_col="r_multiple_after_costs").get("core", {}),
        "cohorts": cohort_split(trades),
        "equity_window": equity_stats(eq_window, STARTING_CASH),
    }


def main() -> None:
    signals, _ = build_signals()
    results = []

    def report(r):
        b, c = r["blended"], r["core_lot"]
        print(f"[{r['config']}] pos={r['positions']} "
              f"exp={b.get('expectancy_r')}R core_exp={c.get('expectancy_r')}R "
              f"core>=5R={c.get('trades_ge_5r')} "
              f"P1={r['cohorts']['P1'].get('expectancy_r')} "
              f"P2={r['cohorts']['P2'].get('expectancy_r')} "
              f"cagr={r['equity_window'].get('cagr_pct')}% "
              f"dd={r['equity_window'].get('max_drawdown_pct')}%", flush=True)

    runs = [
        ("A_baseline", dict(), dict()),
        ("E40_sector_heat", dict(heat_gate=40.0), dict()),
        ("E60_sector_heat", dict(heat_gate=60.0), dict()),
        ("F1_core_patience", dict(), dict(core_patience=True)),
        ("F2_fund_split", dict(), dict(split_mode="fundamental")),
        ("S1_next_open_fill", dict(shift_entry=True), dict(entry_price_col="open")),
        ("S3_gap_aware_stops", dict(), dict(stop_fill="gap_aware")),
    ]
    for name, prep_kw, engine_kw in runs:
        sigs = prep(signals, **prep_kw)
        trades, equity = run_backtest(sigs, min_fundamental_score=0.0,
                                      starting_cash=STARTING_CASH, **engine_kw)
        if trades.empty:
            print(f"[{name}] NO TRADES"); continue
        r = summarize(name, trades, equity)
        results.append(r)
        report(r)

    # S2: baseline under heavier costs (derived from A's saved trades)
    a_trades = pd.read_csv(os.path.join(TRADES_DIR, "A_baseline.csv"),
                           parse_dates=["entry_date", "exit_date"])
    heavy = apply_costs(a_trades, cost_pct_per_side=0.40)
    s2 = trade_stats(heavy, pnl_col="realized_pnl_after_costs",
                     r_col="r_multiple_after_costs")
    print(f"[S2_heavy_costs_0.40] exp={s2.get('expectancy_r')}R "
          f"win%={s2.get('win_rate_pct')} payoff={s2.get('payoff_ratio')}", flush=True)

    lines = ["# Matrix v2 — sector heat, core-lot modulation, execution stress", ""]
    for r in results:
        lines += [f"## {r['config']}",
                  f"- positions: {r['positions']}",
                  f"- blended: {r['blended']}",
                  f"- core lot: {r['core_lot']}",
                  f"- cohorts: {r['cohorts']}",
                  f"- equity (window): {r['equity_window']}", ""]
    lines += ["## S2_heavy_costs_0.40 (derived from A)", f"- blended: {s2}", "",
              "## Pre-registered reading rules",
              "- E: improve expectancy in BOTH cohorts or reject.",
              "- F1/F2: judged on core-lot stats; blended must not degrade materially.",
              "- S1/S2/S3: baseline must stay > +0.5R under every stress.",
              "- Survivor bias applies equally to all rows; compare, don't worship."]
    out = os.path.join(ROOT, "matrix2_report.md")
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"\n-> {out}")


if __name__ == "__main__":
    main()
