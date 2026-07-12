"""
scripts/run_sizing_matrix2.py — pre-registered SIZING sweep v2 (2026-07-12).

Sizing matrix v1 verdicts: slots rejected, risk%% saturates at the 15%% value
cap. v2 declares the two follow-up levers BEFORE seeing results:

  1. SIZING BASIS: the engine sized risk%% + value cap off REMAINING CASH.
     With ~73%% deployed that undersizes every late entry to ~0.3%% real risk.
     Fixed-fractional on marked-to-market EQUITY is the industry standard
     (engine size_on="equity", fills still cash-clamped).
  2. VALUE CAP: 15%% -> 20%% -> 25%% (the v1-identified saturation point).

Grid (7 configs, entries identical everywhere — evidence lock untouched):
  A  cash   cap15 risk1.25   (baseline reproduction)
  B  equity cap15 risk1.25   (isolates the sizing-basis effect)
  C  equity cap20 risk1.25
  D  equity cap25 risk1.25
  E  equity cap20 risk1.75
  F  equity cap25 risk1.75
  G  equity cap20 risk2.50   (does the saturation move?)

CAGR is window-corrected in-script (equity clock spans idle pre-window years).

    python scripts/run_sizing_matrix2.py
"""

from __future__ import annotations

import os
import sys
import time

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

CONFIGS = [
    ("A_cash_cap15_r1.25",   "cash",   15.0, 1.25),
    ("B_equity_cap15_r1.25", "equity", 15.0, 1.25),
    ("C_equity_cap20_r1.25", "equity", 20.0, 1.25),
    ("D_equity_cap25_r1.25", "equity", 25.0, 1.25),
    ("E_equity_cap20_r1.75", "equity", 20.0, 1.75),
    ("F_equity_cap25_r1.75", "equity", 25.0, 1.75),
    ("G_equity_cap20_r2.50", "equity", 20.0, 2.50),
]


def build_signals() -> dict[str, pd.DataFrame]:
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    universe = pd.read_csv(os.path.join(root, "universe.csv"))
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


def corrected_cagr(equity: pd.DataFrame) -> float | None:
    """Re-annualize total return over the ACTIVE window (entries start
    2023-08) instead of the full equity clock (idle pre-window years)."""
    if equity.empty:
        return None
    end_equity = float(equity["equity"].iloc[-1])
    total = end_equity / STARTING_CASH
    end_date = pd.Timestamp(equity["date"].iloc[-1])
    years = max((end_date - WINDOW_START).days / 365.25, 0.5)
    return round((total ** (1 / years) - 1) * 100, 1)


def main() -> None:
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    signals = build_signals()

    results = []
    for name, basis, cap, risk_pct in CONFIGS:
        RISK.max_position_value_pct = cap
        RISK.risk_per_trade_pct = risk_pct
        t0 = time.time()
        trades, equity = run_backtest(
            {s: d.copy() for s, d in signals.items()},
            min_fundamental_score=0.55, starting_cash=STARTING_CASH,
            rank_by="volume", size_on=basis)
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
        r = {"config": name, "basis": basis, "cap": cap, "risk": risk_pct,
             "positions": trades[["name", "entry_date"]].drop_duplicates().shape[0],
             "expectancy_r": blended.get("expectancy_r"),
             "cagr_w_pct": cagr_w, "max_dd_pct": dd,
             "mar": round(cagr_w / abs(dd), 2) if cagr_w is not None and dd else None,
             "p2_exp_r": p2s.get("expectancy_r"),
             "end_equity": round(float(equity["equity"].iloc[-1]), 0),
             "runtime_min": round((time.time() - t0) / 60, 1)}
        results.append(r)
        print(f"[{name}] pos={r['positions']} exp={r['expectancy_r']}R "
              f"cagr_w={cagr_w}% dd={dd}% MAR={r['mar']} p2={r['p2_exp_r']}R",
              flush=True)
        trades.to_csv(os.path.join(root, "matrix_trades", f"SZ2_{name}.csv"), index=False)

    lines = ["# Sizing matrix v2 — sizing basis + value cap (pre-registered 2026-07-12)",
             "",
             "Entries identical in every cell (evidence lock). Window-corrected",
             "CAGR (active window from 2023-08). Survivor-bias caveat applies to",
             "all cells equally; next-open-fill stress kept ~75% of edge — apply",
             "that haircut mentally.", "",
             "| config | pos | exp/R | CAGR(w) | maxDD | MAR | P2 R |",
             "|---|---|---|---|---|---|---|"]
    for r in results:
        if "error" in r:
            lines.append(f"| {r['config']} | {r['error']} |")
            continue
        lines.append(f"| {r['config']} | {r['positions']} | {r['expectancy_r']} "
                     f"| {r['cagr_w_pct']}% | {r['max_dd_pct']}% | {r['mar']} "
                     f"| {r['p2_exp_r']} |")
    lines += ["", "## Reading rules (pre-registered)",
              "- A must reproduce ~21.5% window CAGR / -12.9% DD / +1.29R.",
              "- B vs A isolates the sizing-basis effect alone.",
              "- Adopt only if MAR does not degrade AND maxDD stays inside -20%",
              "  (5pp buffer to the -25% circuit breaker) AND P2 expectancy is",
              "  not materially worse.",
              "- Expectancy/R may shift slightly (bigger fills exhaust cash and",
              "  can skip late same-day candidates) — judge economics via CAGR,",
              "  DD, MAR, and end equity together, not expectancy alone."]
    out = os.path.join(root, "sizing_matrix2_report.md")
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"\n-> {out}")


if __name__ == "__main__":
    main()
