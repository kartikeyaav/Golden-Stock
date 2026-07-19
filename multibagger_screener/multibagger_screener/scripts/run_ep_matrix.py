"""
scripts/run_ep_matrix.py — pre-registered EPISODIC-PIVOT entry-class test
(2026-07-19, strategy_review P3; Bonde/Kullamagi "EP" pattern).

Hypothesis: a violent gap on extreme volume (the market repricing a stock
on new information) is a SECOND technical entry class, independent of the
45-week VCP structure — and therefore also a shot at the young-IPO blind
spot (IREDA/WAAREERTL had no long base to break out of).

EP definition (price/volume only — catalyst verification stays a live-side
news-radar cross-reference, never a backtest input):
  gap  : open >= prev_close * (1 + gap_min)
  vol  : day volume >= vol_mult * avg_vol_50 (prior day's average)
  hold : close > open  AND  close >= prev_close * (1 + gap_min)  (no fade)
  liq  : close >= 20  AND  avg_vol_50 * close >= 1 Cr  AND >= 60 bars history
  stop : LOW OF THE EP DAY (floor 0.75*ATR), entry at the day's close;
         >12% stop-width skip stays (Design Law #7). Two-lot management
         IDENTICAL to baseline (partial 2.5R / 50-DMA trail / weekly 30w).

Grid (pre-registered):
  EP_A   gap>=8%,  vol>=3x            (the canonical Qullamaggie/Bonde spec)
  EP_B   EP_A + neglect: 63-day return before the gap <= +10%  (Bonde's
         "neglected stock" filter — the market REdiscovering something)
  EP_C   gap>=10%, vol>=4x            (stricter — fewer, more violent)
  COMBINED  baseline VCP breakouts UNION EP_A, same 12 shared slots —
         the adoption question is portfolio-level value, not setup vanity.
  BASE   baseline VCP alone, same harness (the incumbent for COMBINED).

All cells: equity basis / cap 15 / risk 1.25 / NIFTY-150 regime scale
(the live sizing rules), window 2023-08 ->, costs applied.

Reading rules (pre-registered):
  - EP class VALIDATES standalone if: >=30 positions, expectancy after
    costs >= +0.5R, P2-cohort expectancy >= 0, maxDD sane (<25%).
  - ADOPT as live capital-bearing alerts only if COMBINED beats BASE on
    MAR with maxDD not >1pp worse. If standalone validates but COMBINED
    is neutral (slot competition), adopt ALERT-ONLY (anticipation-style:
    attention, zero capital) — same disposition logic as V3a.

    python scripts/run_ep_matrix.py
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
from config import RISK, TECHNICAL
from data.cache import list_cached, load_ohlcv
from scoring.technical_score import add_moving_averages, compute_atr

WINDOW_START = pd.Timestamp("2023-08-01")
P1_END = pd.Timestamp("2025-01-01")
MIN_ROWS_VCP = 300
MIN_BARS_EP = 60
STARTING_CASH = 1_000_000
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def ep_frame(df: pd.DataFrame, gap_min: float, vol_mult: float,
             neglect_max: float | None) -> pd.DataFrame:
    """Build an engine-ready signal frame where breakout_today = EP rule
    and stop_override = the EP day's low. Cheap (no VCP calls)."""
    df = add_moving_averages(df).reset_index(drop=True)
    df["atr"] = compute_atr(df)
    iso = df["date"].dt.isocalendar()
    wk = iso["year"].astype(int) * 100 + iso["week"].astype(int)
    df["is_week_end"] = (wk != wk.shift(-1)).fillna(True)
    df["avg_vol_50"] = df["volume"].rolling(50, min_periods=10).mean()

    prev_close = df["close"].shift(1)
    prev_avg_vol = df["avg_vol_50"].shift(1)
    gap_ok = df["open"] >= prev_close * (1 + gap_min)
    vol_ok = df["volume"] >= prev_avg_vol * vol_mult
    hold_ok = (df["close"] > df["open"]) & (df["close"] >= prev_close * (1 + gap_min))
    liq_ok = (df["close"] >= 20) & (prev_avg_vol * df["close"] >= 1e7)
    hist_ok = df.index >= MIN_BARS_EP
    ep = gap_ok & vol_ok & hold_ok & liq_ok & hist_ok
    if neglect_max is not None:
        ret63 = df["close"].shift(1) / df["close"].shift(64) - 1
        ep = ep & (ret63 <= neglect_max)

    df["breakout_today"] = ep.fillna(False)
    # stop = EP-day low, but never TIGHTER than 0.75*ATR below the close
    # (np.minimum = lower price = wider stop; guards the locked-gap case
    # where low ~= close and a noise tick would stop the trade out).
    floor = df["close"] - 0.75 * df["atr"]
    df["stop_override"] = np.where(df["breakout_today"],
                                   np.minimum(df["low"], floor.fillna(df["low"])),
                                   np.nan)
    df["fundamental_score"] = 0.6
    df.loc[df["date"] < WINDOW_START, "breakout_today"] = False
    return df


def build_all(universe: pd.DataFrame, cached: set,
              gap_min: float, vol_mult: float, neglect_max: float | None,
              min_rows: int = MIN_BARS_EP + 5) -> dict[str, pd.DataFrame]:
    out = {}
    for sym in universe["symbol"]:
        if sym not in cached:
            continue
        df = load_ohlcv(sym)
        if df is None or len(df) < min_rows:
            continue
        f = ep_frame(df, gap_min, vol_mult, neglect_max)
        if f["breakout_today"].any():
            out[sym] = f
    return out


def corrected_cagr(equity: pd.DataFrame) -> float | None:
    if equity.empty:
        return None
    total = float(equity["equity"].iloc[-1]) / STARTING_CASH
    years = max((pd.Timestamp(equity["date"].iloc[-1]) - WINDOW_START).days / 365.25, 0.5)
    return round((total ** (1 / years) - 1) * 100, 1)


def nifty_regime() -> pd.Series:
    b = load_ohlcv("NIFTY50").copy()
    b["sma150"] = b["close"].rolling(150).mean()
    return pd.Series(np.where(b["close"] < b["sma150"], 0.5, 1.0),
                     index=pd.DatetimeIndex(b["date"])).dropna()


def run_cell(name, signals, regime, results):
    t0 = time.time()
    trades, equity = run_backtest(
        {s: d.copy() for s, d in signals.items()},
        min_fundamental_score=0.55, starting_cash=STARTING_CASH,
        rank_by="volume", size_on="equity", risk_scale=regime)
    if trades.empty:
        results.append({"config": name, "error": "no trades"})
        print(f"[{name}] NO TRADES", flush=True)
        return
    trades = apply_costs(trades)
    blended = trade_stats(trades, pnl_col="realized_pnl_after_costs",
                          r_col="r_multiple_after_costs")
    eq = equity_stats(equity, STARTING_CASH)
    cagr_w = corrected_cagr(equity)
    dd = eq.get("max_drawdown_pct")
    p2 = trades[trades["entry_date"] >= P1_END]
    p2s = trade_stats(p2, pnl_col="realized_pnl_after_costs",
                      r_col="r_multiple_after_costs") if not p2.empty else {}
    core = trades[trades["lot"] == "core"]
    cs = trade_stats(core, pnl_col="realized_pnl_after_costs",
                     r_col="r_multiple_after_costs") if not core.empty else {}
    r = {"config": name,
         "positions": trades[["name", "entry_date"]].drop_duplicates().shape[0],
         "expectancy_r": blended.get("expectancy_r"),
         "core_exp_r": cs.get("expectancy_r"),
         "win_rate": blended.get("win_rate_pct"),
         "cagr_w_pct": cagr_w, "max_dd_pct": dd,
         "mar": round(cagr_w / abs(dd), 2) if cagr_w is not None and dd else None,
         "p2_exp_r": p2s.get("expectancy_r"),
         "end_equity": round(float(equity["equity"].iloc[-1]), 0)}
    results.append(r)
    print(f"[{name}] pos={r['positions']} exp={r['expectancy_r']}R core={r['core_exp_r']}R "
          f"win={r['win_rate']}% cagr_w={cagr_w}% dd={dd}% MAR={r['mar']} "
          f"p2={r['p2_exp_r']}R ({(time.time()-t0)/60:.1f}m)", flush=True)
    trades.to_csv(os.path.join(ROOT, "matrix_trades", f"EP_{name}.csv"), index=False)


def main() -> None:
    universe = pd.read_csv(os.path.join(ROOT, "universe.csv"))
    cached = set(list_cached())
    regime = nifty_regime()
    results = []

    print("building EP frames...", flush=True)
    t0 = time.time()
    ep_a = build_all(universe, cached, 0.08, 3.0, None)
    ep_b = build_all(universe, cached, 0.08, 3.0, 0.10)
    ep_c = build_all(universe, cached, 0.10, 4.0, None)
    n_a = sum(int(d["breakout_today"].sum()) for d in ep_a.values())
    n_b = sum(int(d["breakout_today"].sum()) for d in ep_b.values())
    n_c = sum(int(d["breakout_today"].sum()) for d in ep_c.values())
    print(f"EP events in window: A={n_a} B={n_b} C={n_c} "
          f"({(time.time()-t0)/60:.1f}m)", flush=True)

    run_cell("EP_A_gap8_vol3", ep_a, regime, results)
    run_cell("EP_B_neglect", ep_b, regime, results)
    run_cell("EP_C_gap10_vol4", ep_c, regime, results)

    # --- BASE + COMBINED (VCP signals are expensive — build once) ---
    print("building VCP baseline signals...", flush=True)
    t0 = time.time()
    vcp: dict[str, pd.DataFrame] = {}
    for i, sym in enumerate(universe["symbol"], 1):
        if sym not in cached:
            continue
        df = load_ohlcv(sym)
        if df is None or len(df) < MIN_ROWS_VCP:
            continue
        sig = generate_signals(df, 0.6)
        sig.loc[sig["date"] < WINDOW_START, "breakout_today"] = False
        vcp[sym] = sig
        if i % 150 == 0:
            print(f"  vcp {i}/{len(universe)} ({time.time()-t0:.0f}s)", flush=True)
    print(f"vcp ready: {len(vcp)} ({(time.time()-t0)/60:.1f}m)", flush=True)

    run_cell("BASE_vcp_only", vcp, regime, results)

    combined: dict[str, pd.DataFrame] = {}
    for sym, vf in vcp.items():
        f = vf.copy()
        if sym in ep_a:
            ef = ep_a[sym][["date", "breakout_today", "stop_override"]].rename(
                columns={"breakout_today": "ep_today"})
            f = f.merge(ef, on="date", how="left")
            f["ep_today"] = f["ep_today"].fillna(False)
            # VCP breakout wins the stop when both fire the same day
            f.loc[f["breakout_today"], "stop_override"] = np.nan
            f["breakout_today"] = f["breakout_today"] | f["ep_today"]
        combined[sym] = f
    for sym, ef in ep_a.items():        # EP-only names (young IPOs etc.)
        if sym not in combined:
            combined[sym] = ef
    run_cell("COMBINED_vcp_plus_epA", combined, regime, results)

    lines = ["# EP matrix — episodic-pivot entry class (pre-registered 2026-07-19)",
             "",
             "Stop = EP-day low (floor 0.75*ATR); two-lot management identical",
             "to baseline; equity basis / cap 15 / risk 1.25 / NIFTY regime.",
             "",
             "| config | pos | exp/R | core/R | win% | CAGR(w) | maxDD | MAR | P2 R |",
             "|---|---|---|---|---|---|---|---|---|"]
    for r in results:
        if "error" in r:
            lines.append(f"| {r['config']} | {r['error']} |")
            continue
        lines.append(f"| {r['config']} | {r['positions']} | {r['expectancy_r']} "
                     f"| {r['core_exp_r']} | {r['win_rate']} | {r['cagr_w_pct']}% "
                     f"| {r['max_dd_pct']}% | {r['mar']} | {r['p2_exp_r']} |")
    lines += ["", "## Adoption rule (pre-registered)",
              "- Standalone validates: >=30 pos, exp >= +0.5R, P2 >= 0, DD < 25%.",
              "- Capital-bearing only if COMBINED > BASE on MAR, DD not >1pp worse.",
              "- Standalone-valid + COMBINED-neutral -> alert-only tier (V3a logic)."]
    out = os.path.join(ROOT, "ep_matrix_report.md")
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"\n-> {out}", flush=True)


if __name__ == "__main__":
    main()
