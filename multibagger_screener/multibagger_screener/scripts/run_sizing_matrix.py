"""
scripts/run_sizing_matrix.py — pre-registered SIZING sweep (2026-07-10).

Entries are evidence-locked (technical-only); SIZING is the one legitimate
lever left (V3b regime sizing already passed as a Pareto improvement). This
sweep answers the user's "21.5% CAGR feels low" question with data: capital
utilization measurement showed avg open risk 0.69%/position vs the nominal
1.25% and the 12-position cap binding on 39% of days — so risk %% and the
position cap are the two knobs declared here, BEFORE results are seen.

Grid (9 configs): risk_per_trade_pct x max_open_positions
    risk  in {1.25 (baseline), 1.75, 2.50}
    slots in {12 (baseline), 16, 20}

Everything else identical to A_baseline: same signals, same window
(2023-08-01 ->), same costs, same two-lot rules. Reading rules at bottom.

    python scripts/run_sizing_matrix.py
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
from config import RISK
from data.cache import list_cached, load_ohlcv

WINDOW_START = pd.Timestamp("2023-08-01")
P1_END = pd.Timestamp("2025-01-01")
MIN_ROWS = 300
STARTING_CASH = 1_000_000

RISK_LEVELS = [1.25, 1.75, 2.50]
SLOT_LEVELS = [12, 16, 20]


def build_signals() -> dict[str, pd.DataFrame]:
    """Technical-only signals (fund const passes the fail-open gate)."""
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


def cohort_split(trades: pd.DataFrame) -> dict:
    out = {}
    for name, mask in [("P1", trades["entry_date"] < P1_END),
                       ("P2", trades["entry_date"] >= P1_END)]:
        sub = trades[mask]
        s = trade_stats(sub, pnl_col="realized_pnl_after_costs",
                        r_col="r_multiple_after_costs") if not sub.empty else {"num_trades": 0}
        out[name] = {"n": s.get("num_trades"), "exp_r": s.get("expectancy_r")}
    return out


def main() -> None:
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    signals = build_signals()

    results = []
    for risk_pct in RISK_LEVELS:
        for slots in SLOT_LEVELS:
            name = f"risk{risk_pct}_slots{slots}"
            RISK.risk_per_trade_pct = risk_pct
            RISK.max_open_positions = slots
            t0 = time.time()
            trades, equity = run_backtest(
                {s: d.copy() for s, d in signals.items()},
                min_fundamental_score=0.55, starting_cash=STARTING_CASH,
                rank_by="volume")
            if trades.empty:
                results.append({"config": name, "error": "no trades"})
                continue
            trades = apply_costs(trades)
            blended = trade_stats(trades, pnl_col="realized_pnl_after_costs",
                                  r_col="r_multiple_after_costs")
            eq = equity_stats(equity, STARTING_CASH)
            cagr = eq.get("cagr_pct")
            dd = eq.get("max_drawdown_pct")
            mar = round(cagr / abs(dd), 2) if cagr is not None and dd else None
            r = {"config": name, "risk_pct": risk_pct, "slots": slots,
                 "positions": trades[["name", "entry_date"]].drop_duplicates().shape[0],
                 "expectancy_r": blended.get("expectancy_r"),
                 "win_rate_pct": blended.get("win_rate_pct"),
                 "cagr_pct": cagr, "max_dd_pct": dd, "mar": mar,
                 "cohorts": cohort_split(trades),
                 "runtime_min": round((time.time() - t0) / 60, 1)}
            results.append(r)
            print(f"[{name}] pos={r['positions']} exp={r['expectancy_r']}R "
                  f"cagr={cagr}% dd={dd}% MAR={mar}", flush=True)
            trades.to_csv(os.path.join(root, "matrix_trades", f"SZ_{name}.csv"), index=False)

    lines = ["# Sizing matrix — pre-registered 2026-07-10", "",
             "Same signals/window/costs as A_baseline; ONLY risk%% and the",
             "position cap vary. Entries untouched (evidence lock).", "",
             "| config | positions | exp/R | CAGR%% | maxDD%% | MAR | P1 R | P2 R |",
             "|---|---|---|---|---|---|---|---|"]
    for r in results:
        if "error" in r:
            lines.append(f"| {r['config']} | {r['error']} |")
            continue
        c = r["cohorts"]
        lines.append(f"| {r['config']} | {r['positions']} | {r['expectancy_r']} "
                     f"| {r['cagr_pct']} | {r['max_dd_pct']} | {r['mar']} "
                     f"| {c['P1']['exp_r']} | {c['P2']['exp_r']} |")
    lines += ["", "## Reading rules (pre-registered)",
              "- Baseline cell is risk1.25_slots12; it must reproduce ~A_baseline.",
              "- Adopt a cell only if it does NOT reduce MAR (CAGR/|maxDD|) and",
              "  keeps maxDD inside the -25% circuit breaker with margin.",
              "- Expectancy/R should be ~flat across cells (sizing must not",
              "  change per-trade edge much; big drops = crowding-out effects).",
              "- P2 (chop cohort) must not get materially worse.",
              "- Survivor bias applies equally to all cells; compare cells,",
              "  don't trust absolutes. Next-open-fill stress kept ~75% of edge;",
              "  apply that haircut mentally to every CAGR here."]
    out = os.path.join(root, "sizing_matrix_report.md")
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"\n-> {out}")


if __name__ == "__main__":
    main()
