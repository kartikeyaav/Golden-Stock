"""
scripts/run_sizing_matrix3.py — pre-registered SIZING-OVERLAY sweep v3
(2026-07-19, strategy_review P1+P2).

Question: can a smarter RISK SCALE beat the adopted binary NIFTY/150-DMA
rule (V3b)? Two families, declared before results:

  P1 BREADTH (O'Neil market-model, internalized): % of the universe above
     its own 200-DMA — computed from our own cache, no new data.
  P2 PROGRESSIVE EXPOSURE (Minervini): scale risk off the portfolio's OWN
     trailing results (trades or equity curve). Point-in-time by
     construction (engine calls the fn before the day's entries).

Entries are IDENTICAL in every cell (evidence lock §2B untouched — this is
sizing only). Equity basis, cap 15, risk 1.25 everywhere (the adopted
canon). Window/costs/universe identical to sizing matrix v2.

Grid (8 configs):
  A_SZ2B_repro      equity, NO overlay          (sanity: must reproduce SZ2 B)
  B_live_nifty150   + NIFTY<150dma -> 0.5       (THE INCUMBENT = live rule)
  C_breadth_graded  breadth <40% -> 0.5, 40-60% -> 0.75, else 1.0 (replaces NIFTY)
  D_breadth_binary  breadth <50% -> 0.5, else 1.0                 (replaces NIFTY)
  E_breadth_and_nifty  min(C, NIFTY rule)        (defensive union)
  F_pe_trades       NIFTY rule x PE: mean R of last 10 closed trades < 0 -> 0.5
                    (fewer than 5 closed trades -> neutral 1.0)
  G_pe_equity       NIFTY rule x PE: equity < its own 50-obs SMA -> 0.5
  H_combo           C (breadth graded) x F's trade-feedback PE

Reading rules (pre-registered, mirrors V3b/SZ2):
  - A must reproduce SZ2 B (~47.4% window CAGR / -18.5% DD) within noise.
  - Adopt a variant ONLY if, vs B_live_nifty150: MAR >= incumbent AND
    maxDD not worse by >1pp AND window CAGR not lower by >1pp AND P2-cohort
    expectancy not materially worse (>-0.05R). Ties -> simplest rule wins.
  - Overlays change SIZING only; if trades differ it is only via the cash
    path (smaller fills free cash sooner) — flag any position-count drift.

    python scripts/run_sizing_matrix3.py
"""

from __future__ import annotations

import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backtest.engine import generate_signals, run_backtest
from backtest.metrics import apply_costs, equity_stats, trade_stats
from config import RISK
from data.cache import list_cached, load_ohlcv

WINDOW_START = pd.Timestamp("2023-08-01")
P1_END = pd.Timestamp("2025-01-01")
MIN_ROWS = 300
STARTING_CASH = 1_000_000

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def build_signals() -> dict[str, pd.DataFrame]:
    universe = pd.read_csv(os.path.join(ROOT, "universe.csv"))
    cached = set(list_cached())
    signals: dict[str, pd.DataFrame] = {}
    t0 = time.time()
    for i, sym in enumerate(universe["symbol"], 1):
        if sym not in cached:
            continue
        df = load_ohlcv(sym)
        if df is None or len(df) < MIN_ROWS:
            continue
        sig = generate_signals(df, 0.6)
        sig.loc[sig["date"] < WINDOW_START, "breakout_today"] = False
        signals[sym] = sig
        if i % 100 == 0:
            print(f"  signals {i}/{len(universe)} ({time.time()-t0:.0f}s)", flush=True)
    print(f"signals ready: {len(signals)} stocks in {(time.time()-t0)/60:.1f} min", flush=True)
    return signals


def build_breadth(signals: dict[str, pd.DataFrame]) -> pd.Series:
    """% of universe stocks closing above their own 200-DMA, per date.
    Uses the SAME frames the engine trades (sma_200 already computed).
    Dates with <100 reporting stocks stay neutral (dropped -> ffill)."""
    counts: dict[pd.Timestamp, list[int]] = {}
    for df in signals.values():
        sub = df[["date", "close", "sma_200"]].dropna()
        for d, c, s in zip(sub["date"], sub["close"], sub["sma_200"]):
            above, tot = counts.setdefault(d, [0, 0])
            counts[d][1] = tot + 1
            if c > s:
                counts[d][0] = above + 1
    rows = [(d, a / t * 100) for d, (a, t) in sorted(counts.items()) if t >= 100]
    s = pd.Series([p for _, p in rows], index=pd.DatetimeIndex([d for d, _ in rows]))
    return s


def nifty_regime() -> pd.Series:
    b = load_ohlcv("NIFTY50")
    b = b.copy()
    b["sma150"] = b["close"].rolling(150).mean()
    s = pd.Series(np.where(b["close"] < b["sma150"], 0.5, 1.0),
                  index=pd.DatetimeIndex(b["date"]))
    return s.dropna()


def breadth_graded(breadth: pd.Series) -> pd.Series:
    return pd.Series(np.where(breadth < 40, 0.5, np.where(breadth < 60, 0.75, 1.0)),
                     index=breadth.index)


def breadth_binary(breadth: pd.Series) -> pd.Series:
    return pd.Series(np.where(breadth < 50, 0.5, 1.0), index=breadth.index)


# --- progressive-exposure callbacks (point-in-time: see only closed state) ---

def pe_trades(portfolio, date) -> float:
    closed = portfolio.closed_trades
    if len(closed) < 5:
        return 1.0
    last = closed[-10:]
    rs = []
    for t in last:
        denom = sum(l.shares for l in t.lots) * t.risk_per_share
        if denom > 0:
            rs.append(sum(l.realized_pnl for l in t.lots) / denom)
    if not rs:
        return 1.0
    return 0.5 if float(np.mean(rs)) < 0 else 1.0


def pe_equity(portfolio, date) -> float:
    curve = portfolio.equity_curve
    if len(curve) < 50:
        return 1.0
    eq = [p["equity"] for p in curve[-50:]]
    return 0.5 if eq[-1] < float(np.mean(eq)) else 1.0


def corrected_cagr(equity: pd.DataFrame) -> float | None:
    if equity.empty:
        return None
    total = float(equity["equity"].iloc[-1]) / STARTING_CASH
    years = max((pd.Timestamp(equity["date"].iloc[-1]) - WINDOW_START).days / 365.25, 0.5)
    return round((total ** (1 / years) - 1) * 100, 1)


def main() -> None:
    signals = build_signals()
    print("building breadth series...", flush=True)
    breadth = build_breadth(signals)
    print(f"breadth: {len(breadth)} dates, latest {breadth.index[-1].date()} = "
          f"{breadth.iloc[-1]:.1f}% above 200dma", flush=True)
    nifty = nifty_regime()
    br_g, br_b = breadth_graded(breadth), breadth_binary(breadth)
    br_and_nifty = pd.concat([br_g, nifty], axis=1).ffill().min(axis=1).dropna()

    CONFIGS = [
        ("A_SZ2B_repro",       None,          None),
        ("B_live_nifty150",    nifty,         None),
        ("C_breadth_graded",   br_g,          None),
        ("D_breadth_binary",   br_b,          None),
        ("E_breadth_and_nifty", br_and_nifty, None),
        ("F_pe_trades",        nifty,         pe_trades),
        ("G_pe_equity",        nifty,         pe_equity),
        ("H_combo",            br_g,          pe_trades),
    ]

    RISK.max_position_value_pct = 15.0
    RISK.risk_per_trade_pct = 1.25

    results = []
    for name, scale_series, scale_fn in CONFIGS:
        t0 = time.time()
        trades, equity = run_backtest(
            {s: d.copy() for s, d in signals.items()},
            min_fundamental_score=0.55, starting_cash=STARTING_CASH,
            rank_by="volume", size_on="equity",
            risk_scale=scale_series, risk_scale_fn=scale_fn)
        if trades.empty:
            results.append({"config": name, "error": "no trades"})
            continue
        trades = apply_costs(trades)
        blended = trade_stats(trades, pnl_col="realized_pnl_after_costs",
                              r_col="r_multiple_after_costs")
        eq = equity_stats(equity, STARTING_CASH)
        cagr_w = corrected_cagr(equity)
        dd = eq.get("max_drawdown_pct")
        p2 = trades[trades["entry_date"] >= P1_END]
        p2s = trade_stats(p2, pnl_col="realized_pnl_after_costs",
                          r_col="r_multiple_after_costs") if not p2.empty else {}
        r = {"config": name,
             "positions": trades[["name", "entry_date"]].drop_duplicates().shape[0],
             "expectancy_r": blended.get("expectancy_r"),
             "cagr_w_pct": cagr_w, "max_dd_pct": dd,
             "mar": round(cagr_w / abs(dd), 2) if cagr_w is not None and dd else None,
             "p2_exp_r": p2s.get("expectancy_r"),
             "end_equity": round(float(equity["equity"].iloc[-1]), 0),
             "runtime_min": round((time.time() - t0) / 60, 1)}
        results.append(r)
        print(f"[{name}] pos={r['positions']} exp={r['expectancy_r']}R "
              f"cagr_w={cagr_w}% dd={dd}% MAR={r['mar']} p2={r['p2_exp_r']}R "
              f"({r['runtime_min']}m)", flush=True)
        trades.to_csv(os.path.join(ROOT, "matrix_trades", f"SZ3_{name}.csv"), index=False)

    lines = ["# Sizing matrix v3 — breadth + progressive-exposure overlays "
             "(pre-registered 2026-07-19)", "",
             "Entries identical in every cell (sizing only — evidence lock",
             "untouched). Equity basis / cap 15 / risk 1.25 everywhere.",
             "Incumbent = B_live_nifty150 (the adopted V3b rule).", "",
             "| config | pos | exp/R | CAGR(w) | maxDD | MAR | P2 R |",
             "|---|---|---|---|---|---|---|"]
    for r in results:
        if "error" in r:
            lines.append(f"| {r['config']} | {r['error']} |")
            continue
        lines.append(f"| {r['config']} | {r['positions']} | {r['expectancy_r']} "
                     f"| {r['cagr_w_pct']}% | {r['max_dd_pct']}% | {r['mar']} "
                     f"| {r['p2_exp_r']} |")
    lines += ["", "## Adoption rule (pre-registered)",
              "- vs B: MAR >= incumbent AND maxDD not >1pp worse AND CAGR not",
              "  >1pp lower AND P2 expectancy not worse than -0.05R.",
              "- Ties -> simplest rule. A must reproduce SZ2 B within noise."]
    out = os.path.join(ROOT, "sizing_matrix3_report.md")
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"\n-> {out}", flush=True)


if __name__ == "__main__":
    main()
