"""
scripts/run_matrix3.py — matrix v3, pre-registered. Tests the two hypotheses
matrices v1/v2 left open:

  A       technical baseline (reference re-run)
  V3a-F   ANTICIPATION entries WITH fundamentals: weekly Stage-1 base
          (flat 30wMA, lower half of 52w range) + base depth <= 40% + within
          25% of 52w high + RS improving (13w > 26w ratio) + PIT fundamental
          score >= 0.60. Entry at that week's close; standard two-lot rules.
          THE anticipation-tier hypothesis: fundamentals lead price in bases.
  V3a-P   Same WITHOUT the fundamental condition (isolates price-only value).
  V3b     Baseline entries, REGIME-SIZED: risk budget x0.5 whenever NIFTY50
          closes below its 150-DMA. Sizing, never a filter — entries unchanged.

Structural caveat, declared up front: anticipation entries sit near a flat
30-week MA by construction, so the core lot's weekly-MA exit will trigger
fast on any weak week — results measure the tier AS IT WOULD ACTUALLY RUN
under locked management rules, not a bespoke fantasy version.

    python scripts/run_matrix3.py
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
ANTICIPATION_FUND_MIN = 0.60
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRADES_DIR = os.path.join(ROOT, "matrix_trades")


def anticipation_mask(df: pd.DataFrame, bench: pd.DataFrame,
                      fund: pd.Series | None) -> pd.Series:
    """Vectorized weekly anticipation trigger mapped onto daily rows.
    True only on the week-end row where all conditions first hold."""
    d = df.set_index("date")
    wk_close = d["close"].resample("W-FRI").last()
    wk_high = d["high"].resample("W-FRI").max()
    wk_low = d["low"].resample("W-FRI").min()

    ma30 = wk_close.rolling(30).mean()
    slope = (ma30 / ma30.shift(8) - 1) * 100
    hi52 = wk_high.rolling(52).max()
    lo52 = wk_low.rolling(52).min()
    pos52 = (wk_close - lo52) / (hi52 - lo52)

    stage1 = slope.abs().le(1.5) & pos52.lt(0.5)

    base_low_since = wk_low.rolling(52).min()  # approximation of base low
    base_depth = (hi52 - base_low_since) / hi52 * 100
    near_high = wk_close >= hi52 * 0.75
    depth_ok = base_depth <= 40.0

    b = bench.set_index("date")["close"].resample("W-FRI").last()
    ratio = ((1 + wk_close.pct_change(13)) / (1 + b.pct_change(13).reindex(wk_close.index)))
    ratio26 = ((1 + wk_close.pct_change(26)) / (1 + b.pct_change(26).reindex(wk_close.index)))
    rs_improving = ratio > ratio26

    trigger = stage1 & depth_ok & near_high & rs_improving
    if fund is not None and not fund.empty:
        f = fund.copy()
        f.index = pd.to_datetime(f.index)
        fund_wk = f.reindex(wk_close.index, method="ffill")
        trigger = trigger & (fund_wk >= ANTICIPATION_FUND_MIN)

    # weekly trigger -> the matching daily week-end row
    daily = pd.Series(False, index=d.index)
    week_of_day = d.index.to_series().dt.to_period("W-FRI")
    trigger_weeks = set(trigger[trigger.fillna(False)].index.to_period("W-FRI"))
    is_week_end = week_of_day != week_of_day.shift(-1)
    daily[(week_of_day.isin(trigger_weeks)) & is_week_end] = True
    return daily.reset_index(drop=True)


def cohorts(trades):
    out = {}
    for name, mask in [("P1", trades["entry_date"] < P1_END),
                       ("P2", trades["entry_date"] >= P1_END)]:
        sub = trades[mask]
        s = trade_stats(sub, pnl_col="realized_pnl_after_costs",
                        r_col="r_multiple_after_costs") if not sub.empty else {"num_trades": 0}
        out[name] = {k: s.get(k) for k in ("num_trades", "expectancy_r", "win_rate_pct")}
    return out


def summarize(name, trades, equity):
    trades = apply_costs(trades)
    os.makedirs(TRADES_DIR, exist_ok=True)
    trades.to_csv(os.path.join(TRADES_DIR, f"{name}.csv"), index=False)
    eq = equity_stats(equity[equity["date"] >= WINDOW_START], STARTING_CASH)
    return {
        "config": name,
        "positions": trades[["name", "entry_date"]].drop_duplicates().shape[0],
        "blended": trade_stats(trades, pnl_col="realized_pnl_after_costs",
                               r_col="r_multiple_after_costs"),
        "core": lot_breakdown(trades, pnl_col="realized_pnl_after_costs",
                              r_col="r_multiple_after_costs").get("core", {}),
        "cohorts": cohorts(trades),
        "equity": eq,
    }


def main() -> None:
    universe = pd.read_csv(os.path.join(ROOT, "universe.csv"))
    industry_by_sym = dict(zip(universe["symbol"], universe["industry"]))
    cached = set(list_cached())
    bench = load_ohlcv("NIFTY50")

    signals, anti_fund, anti_price = {}, {}, {}
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
        signals[sym] = sig

        m_f = anticipation_mask(df, bench, series if not series.empty else None)
        m_p = anticipation_mask(df, bench, None)
        in_window = sig["date"] >= WINDOW_START
        anti_fund[sym] = (m_f & in_window).to_numpy()
        anti_price[sym] = (m_p & in_window).to_numpy()
        if i % 100 == 0:
            print(f"  signals {i}/{len(universe)} ({time.time()-t0:.0f}s)", flush=True)
    print(f"signals ready: {len(signals)} in {(time.time()-t0)/60:.1f} min", flush=True)

    # regime series: NIFTY50 below its 150-DMA -> half risk
    b = bench.copy()
    b["sma150"] = b["close"].rolling(150).mean()
    regime = pd.Series(np.where(b["close"] < b["sma150"], 0.5, 1.0),
                       index=pd.to_datetime(b["date"]))

    results = []

    def run(name, sigs, **kw):
        trades, equity = run_backtest(sigs, min_fundamental_score=0.0,
                                      starting_cash=STARTING_CASH, **kw)
        if trades.empty:
            print(f"[{name}] NO TRADES"); return
        r = summarize(name, trades, equity)
        results.append(r)
        print(f"[{name}] pos={r['positions']} exp={r['blended'].get('expectancy_r')}R "
              f"core={r['core'].get('expectancy_r')}R "
              f"P1={r['cohorts']['P1'].get('expectancy_r')} "
              f"P2={r['cohorts']['P2'].get('expectancy_r')} "
              f"cagr={r['equity'].get('cagr_pct')}% dd={r['equity'].get('max_drawdown_pct')}%",
              flush=True)

    run("A_baseline_ref", signals)

    for name, masks in [("V3a_anticipation_fund", anti_fund),
                        ("V3a_anticipation_priceonly", anti_price)]:
        sigs = {}
        for sym, df in signals.items():
            d = df.copy()
            d["breakout_today"] = masks[sym]
            sigs[sym] = d
        run(name, sigs)

    run("V3b_regime_sized", signals, risk_scale=regime)

    lines = ["# Matrix v3 — anticipation tier + regime sizing", ""]
    for r in results:
        lines += [f"## {r['config']}", f"- positions: {r['positions']}",
                  f"- blended: {r['blended']}", f"- core: {r['core']}",
                  f"- cohorts: {r['cohorts']}", f"- equity: {r['equity']}", ""]
    lines += ["## Pre-registered reading rules",
              "- V3a-F earns the anticipation tier capital ONLY if expectancy is",
              "  positive in both cohorts AND beats V3a-P (fundamentals must add",
              "  value over price-only anticipation).",
              "- V3b judged on drawdown + Sharpe-like smoothness vs baseline;",
              "  it trades CAGR for safety by design.",
              "- Structural caveat: core exits fire fast near a flat 30wMA —",
              "  declared before running."]
    out = os.path.join(ROOT, "matrix3_report.md")
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"\n-> {out}")


if __name__ == "__main__":
    main()
