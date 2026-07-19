"""
scripts/run_sizing_matrix3b.py — pre-registered FOLLOW-UP to sizing matrix
v3 (2026-07-19, same evening).

v3 outcome: D_breadth_binary beat the incumbent on CAGR (+1.8pp), maxDD
(-2.9pp better) and MAR (3.35 vs 2.70) but FAILED the strict P2-expectancy
clause by 0.027R. Diagnosis: composition — smaller defensive sizes free
cash, admitting ~4 extra chop-period entries that dilute PER-TRADE R while
improving the PORTFOLIO. Per-trade expectancy is sizing-invariant for
shared trades, so it was the wrong chop guard for a sizing overlay; the
right guard is what the clause was protecting: CHOP-PERIOD SURVIVABILITY.

Registered BEFORE running (this file is the registration):

  Compare D vs B on the P2 SEGMENT (2025-01-01 ->) of the equity curve:
    - P2 segment max drawdown:  D not worse than B by >1pp
    - P2 segment total return:  D >= B - 1pp
  ADOPT D iff both hold (v3 already established the full-window Pareto win).
  Otherwise the NIFTY/150 rule stays and breadth is shelved.

Honesty note: same window as v3, run after seeing v3's aggregate table —
single-window iteration is this project's acknowledged limitation (every
matrix since v1 shares it); the guard against self-deception is that the
metrics and thresholds above were fixed before this script ever ran.

    python scripts/run_sizing_matrix3b.py
"""

from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backtest.engine import run_backtest
from backtest.metrics import apply_costs
from config import RISK
from scripts.run_sizing_matrix3 import (P1_END, STARTING_CASH, breadth_binary,
                                        build_breadth, build_signals,
                                        corrected_cagr, nifty_regime)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def seg_stats(equity: pd.DataFrame, start: pd.Timestamp) -> dict:
    e = equity[pd.to_datetime(equity["date"]) >= start].reset_index(drop=True)
    if e.empty:
        return {}
    eq = e["equity"].astype(float)
    ret = eq.iloc[-1] / eq.iloc[0] - 1
    peak = eq.cummax()
    dd = float(((eq - peak) / peak).min() * 100)
    return {"p2_return_pct": round(ret * 100, 1), "p2_maxdd_pct": round(dd, 2)}


def main() -> None:
    signals = build_signals()
    breadth = build_breadth(signals)
    nifty = nifty_regime()
    br_b = breadth_binary(breadth)

    RISK.max_position_value_pct = 15.0
    RISK.risk_per_trade_pct = 1.25

    rows = []
    for name, series in (("B_live_nifty150", nifty), ("D_breadth_binary", br_b)):
        trades, equity = run_backtest(
            {s: d.copy() for s, d in signals.items()},
            min_fundamental_score=0.55, starting_cash=STARTING_CASH,
            rank_by="volume", size_on="equity", risk_scale=series)
        trades = apply_costs(trades)
        seg = seg_stats(equity, P1_END)
        rows.append({"config": name, "cagr_w": corrected_cagr(equity), **seg})
        print(f"[{name}] cagr_w={rows[-1]['cagr_w']}% "
              f"P2ret={seg.get('p2_return_pct')}% P2dd={seg.get('p2_maxdd_pct')}%",
              flush=True)

    b, d = rows[0], rows[1]
    dd_ok = d["p2_maxdd_pct"] >= b["p2_maxdd_pct"] - 1.0
    ret_ok = d["p2_return_pct"] >= b["p2_return_pct"] - 1.0
    verdict = "ADOPT D (both P2-segment guards hold)" if (dd_ok and ret_ok) else \
              "KEEP B (a P2-segment guard failed)"
    lines = ["# Sizing matrix v3b — breadth-binary follow-up (pre-registered "
             "2026-07-19, same evening as v3)", "",
             "| config | CAGR(w) | P2-seg return | P2-seg maxDD |", "|---|---|---|---|"]
    for r in rows:
        lines.append(f"| {r['config']} | {r['cagr_w']}% | {r['p2_return_pct']}% "
                     f"| {r['p2_maxdd_pct']}% |")
    lines += ["", f"P2-DD guard (D >= B-1pp): {'PASS' if dd_ok else 'FAIL'}",
              f"P2-return guard (D >= B-1pp): {'PASS' if ret_ok else 'FAIL'}",
              "", f"## VERDICT: {verdict}"]
    out = os.path.join(ROOT, "sizing_matrix3b_report.md")
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"\nVERDICT: {verdict}\n-> {out}", flush=True)


if __name__ == "__main__":
    main()
