"""
scripts/run_trail_slot_matrix.py — P6 (trailing speed) + P5b (slot count on
equity-basis sizing). Both PRE-REGISTERED in PREREG_2026-07-27.md, which was
committed before this script was run.

    python scripts/run_trail_slot_matrix.py            # both
    python scripts/run_trail_slot_matrix.py --only p6

P6 varies ONLY the trading lot's trailing MA (10/20/30/50). The core lot keeps
its weekly 30-week-MA rule — F1 and F2 both showed that touching core-lot
behaviour destroys the edge, so the run must not be able to reach it. The
control (trail 50) must reproduce SZ2_B, and the core lot's R must be identical
across cells; if it moves, the cells are not isolating what they claim and the
run is VOID.

P5b re-opens slot count (rejected 2026-07-11) because that matrix ran on
CASH-basis sizing — the defect corrected 2026-07-12. Per-trade R is
scale-invariant so the expectancy finding survives; the CAGR/MAR comparison
does not, because the bug distorted deployed capital unevenly across slot
counts.

Entries are identical in every cell of both matrices. Evidence lock untouched.
"""

from __future__ import annotations

import argparse
import os
import sys
import time

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backtest.engine import generate_signals, run_backtest
from backtest.metrics import apply_costs, equity_stats, trade_stats
from config import RISK
from data.cache import list_cached, load_ohlcv

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WINDOW_START = pd.Timestamp("2023-08-01")
P1_END = pd.Timestamp("2025-01-01")
MIN_ROWS = 300
STARTING_CASH = 1_000_000

# (label, trail_ma, slots)  — baseline is trail 50 / 12 slots
P6_CELLS = [("P6_trail50_control", 50, 12),
            ("P6_trail30", 30, 12),
            ("P6_trail20", 20, 12),
            ("P6_trail10", 10, 12)]
P5B_CELLS = [("P5b_slots12_control", 50, 12),
             ("P5b_slots08", 50, 8),
             ("P5b_slots16", 50, 16),
             ("P5b_slots20", 50, 20)]


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
        if i % 150 == 0:
            print(f"  signals {i}/{len(universe)} ({time.time()-t0:.0f}s)", flush=True)
    print(f"signals ready: {len(signals)} stocks in {(time.time()-t0)/60:.1f} min",
          flush=True)
    return signals


def corrected_cagr(equity: pd.DataFrame) -> float | None:
    """Re-annualize over the ACTIVE window (entries start 2023-08), not the
    full equity clock which carries idle pre-window years."""
    if equity.empty:
        return None
    total = float(equity["equity"].iloc[-1]) / STARTING_CASH
    years = max((pd.Timestamp(equity["date"].iloc[-1]) - WINDOW_START).days / 365.25, 0.5)
    return round((total ** (1 / years) - 1) * 100, 1)


def run_cell(signals: dict, label: str, trail_ma: int, slots: int) -> dict:
    prev_slots = RISK.max_open_positions
    RISK.max_open_positions = slots
    try:
        t0 = time.time()
        trades, equity = run_backtest(
            {s: d.copy() for s, d in signals.items()},
            min_fundamental_score=0.55, starting_cash=STARTING_CASH,
            rank_by="volume", size_on="equity",
            trail_ma=None if trail_ma == RISK.trailing_ma_period else trail_ma)
    finally:
        RISK.max_open_positions = prev_slots
    if trades.empty:
        return {"config": label, "error": "no trades"}
    trades = apply_costs(trades)
    blended = trade_stats(trades, pnl_col="realized_pnl_after_costs",
                          r_col="r_multiple_after_costs")
    eq = equity_stats(equity, STARTING_CASH)
    cagr_w, dd = corrected_cagr(equity), eq.get("max_drawdown_pct")
    p2 = trades[trades["entry_date"] >= P1_END]
    p2s = (trade_stats(p2, pnl_col="realized_pnl_after_costs",
                       r_col="r_multiple_after_costs") if not p2.empty else {})

    def lot_r(lot: str):
        rows = trades[trades["lot"] == lot]
        return round(float(rows["r_multiple_after_costs"].mean()), 3) if len(rows) else None

    r = {"config": label, "trail_ma": trail_ma, "slots": slots,
         "positions": trades[["name", "entry_date"]].drop_duplicates().shape[0],
         "expectancy_r": blended.get("expectancy_r"),
         "trading_lot_r": lot_r("trading"), "core_lot_r": lot_r("core"),
         "cagr_w_pct": cagr_w, "max_dd_pct": dd,
         "mar": round(cagr_w / abs(dd), 2) if cagr_w is not None and dd else None,
         "p2_exp_r": p2s.get("expectancy_r"),
         "runtime_min": round((time.time() - t0) / 60, 1)}
    print(f"[{label}] pos={r['positions']} exp={r['expectancy_r']}R "
          f"(trading {r['trading_lot_r']} / core {r['core_lot_r']}) "
          f"cagr_w={cagr_w}% dd={dd}% MAR={r['mar']} p2={r['p2_exp_r']}R", flush=True)
    trades.to_csv(os.path.join(ROOT, "matrix_trades", f"{label}.csv"), index=False)
    return r


def _table(rows: list[dict], extra: str) -> list[str]:
    out = [f"| config | {extra} | pos | exp/R | trading lot | core lot | CAGR(w) | maxDD | MAR | P2 R |",
           "|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        if r.get("error"):
            out.append(f"| {r['config']} | — | — | {r['error']} | | | | | | |")
            continue
        key = r["trail_ma"] if extra == "trail" else r["slots"]
        out.append(f"| {r['config']} | {key} | {r['positions']} | {r['expectancy_r']} | "
                   f"{r['trading_lot_r']} | {r['core_lot_r']} | {r['cagr_w_pct']}% | "
                   f"{r['max_dd_pct']}% | {r['mar']} | {r['p2_exp_r']} |")
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", choices=["p5b", "p6"], help="run one matrix")
    args = ap.parse_args()

    signals = build_signals()
    lines = ["# P6 trailing speed + P5b slot count — pre-registered 2026-07-27",
             "",
             "Reading rules are fixed in `PREREG_2026-07-27.md`, committed before",
             "this ran. Entries identical in every cell (evidence lock).",
             "Window-corrected CAGR (active window from 2023-08). Survivor bias",
             "applies to all cells equally — compare cells, not the outside world.",
             ""]

    if args.only != "p5b":
        print("\n=== P6 trailing speed (trading lot only) ===", flush=True)
        p6 = [run_cell(signals, *c) for c in P6_CELLS]
        lines += ["## P6 — trading-lot trailing MA", ""] + _table(p6, "trail") + [""]
        ctrl = next((r for r in p6 if "control" in r["config"]), {})
        cores = [r.get("core_lot_r") for r in p6 if not r.get("error")]
        if len(set(cores)) > 1:
            lines += ["**VOID as an isolated test**: the core lot's R moved across "
                      f"cells ({cores}). The trailing MA was supposed to touch the "
                      "trading lot only, so these cells are not measuring what "
                      "they claim.", ""]
        else:
            lines += [f"Core lot identical across cells ({cores[0] if cores else '—'}R) "
                      "— the test isolated the trading lot as intended.", ""]
        lines += [f"Control expectancy {ctrl.get('expectancy_r')}R "
                  f"(must reproduce SZ2_B's +1.612R within ±0.05R).", ""]

    if args.only != "p6":
        print("\n=== P5b slot count (equity-basis sizing) ===", flush=True)
        p5b = [run_cell(signals, *c) for c in P5B_CELLS]
        lines += ["## P5b — slot count, equity-basis sizing", ""] + _table(p5b, "slots") + [""]

    out = os.path.join(ROOT, "trail_slot_matrix_report.md")
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"\n-> {out}")


if __name__ == "__main__":
    main()
