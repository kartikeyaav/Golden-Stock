"""
scripts/run_honest_rerun.py — re-measure the strategy the system ACTUALLY
runs, on the corrected engine, over the whole history, beside two controls a
sceptic would ask for. Research diagnostic, 2026-09-25. It changes no live
rule; it answers "is the strategy holding up, and is there a better one?".

Why this run exists
-------------------
1. The live configuration was never run as one backtest. Breadth-regime
   sizing was adopted on the VCP-only family and the EP class on a
   NIFTY-regime run (config.EVIDENCE.combined_note says so). The live system
   is the UNION of the two.
2. The headline numbers came from a 2.9-year window starting 2023-08 — the
   start of one of the strongest small-cap bull runs on record. This run adds
   the full window the cache supports (signals from ~2020 after warm-up):
   the COVID crash, the 2021 run, the 2022 chop, 2023-24, the 2025 drawdown.
3. AUDIT 2026-09-22 reproduced three engine defects. They are fixed behind
   opt-in parameters (history reproduces byte-for-byte without them):
     F3 entry_day_stop     — an open fill is checked against its own bar
     F4 cost_pct_per_side  — fees debited in the ledger, so CAGR/DD are net
     F6 week_end_flags     — the last bar closes a week only on a Friday
4. Controls on the SAME universe and dates, so survivor bias is shared:
     EQW   equal-weight every name with data, rebalanced monthly
     MOM   momentum rotation: volatility-adjusted 6m+12m momentum (the NSE
           momentum-index construction), top 20, monthly, hold until rank>40,
           trades at the next session's open, same costs
     MOM_R MOM with the system's own breadth rule (half invested <50%)

Universe: the 650 index names (index_source != nse_gap) — the universe every
prior matrix used, so the rows are comparable with VALIDATION_REPORT.

    python scripts/run_honest_rerun.py
Writes honest_rerun_report.md and matrix_trades/HR_*.csv.
"""

from __future__ import annotations

import json
import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backtest.engine import generate_signals, run_backtest, week_end_flags
from backtest.metrics import apply_costs, trade_stats
from data.cache import list_cached, load_ohlcv
from scoring import momentum
from scoring.technical_score import add_moving_averages, compute_atr

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STARTING_CASH = 1_000_000
EP_WINDOW = pd.Timestamp("2023-08-01")     # the window every headline used
FULL_WINDOW = pd.Timestamp("2020-01-01")   # first date with warmed-up signals
MIN_ROWS_VCP = 300
MIN_BARS_EP = 60
COST_BASE = 0.15        # % per side — the project's standing estimate
COST_STRESS = 0.25      # % per side — small-cap slippage under stress
RF_PCT = 6.5            # Indian T-bill proxy for Sharpe


# ---------------------------------------------------------------------------
# signal frames (identical construction to run_ep_matrix / run_sizing_matrix3)
# ---------------------------------------------------------------------------
def ep_frame(df: pd.DataFrame, gap_min: float = 0.08, vol_mult: float = 3.0) -> pd.DataFrame:
    df = add_moving_averages(df).reset_index(drop=True)
    df["atr"] = compute_atr(df)
    df["is_week_end"] = week_end_flags(df["date"])
    df["avg_vol_50"] = df["volume"].rolling(50, min_periods=10).mean()
    prev_close = df["close"].shift(1)
    prev_avg_vol = df["avg_vol_50"].shift(1)
    ep = ((df["open"] >= prev_close * (1 + gap_min))
          & (df["volume"] >= prev_avg_vol * vol_mult)
          & (df["close"] > df["open"]) & (df["close"] >= prev_close * (1 + gap_min))
          & (df["close"] >= 20) & (prev_avg_vol * df["close"] >= 1e7)
          & (df.index >= MIN_BARS_EP))
    df["breakout_today"] = ep.fillna(False)
    floor = df["close"] - 0.75 * df["atr"]
    df["stop_override"] = np.where(df["breakout_today"],
                                   np.minimum(df["low"], floor.fillna(df["low"])), np.nan)
    df["fundamental_score"] = 0.6
    return df


def combine(vcp: dict, ep: dict) -> dict:
    out = {}
    for sym, vf in vcp.items():
        f = vf.copy()
        if sym in ep:
            ef = ep[sym][["date", "breakout_today", "stop_override"]].rename(
                columns={"breakout_today": "ep_today"})
            f = f.merge(ef, on="date", how="left")
            f["ep_today"] = f["ep_today"].fillna(False).astype(bool)
            f.loc[f["breakout_today"], "stop_override"] = np.nan
            f["breakout_today"] = f["breakout_today"] | f["ep_today"]
        out[sym] = f
    for sym, ef in ep.items():
        if sym not in out:
            out[sym] = ef
    return out


def windowed(frames: dict, start: pd.Timestamp, shift_entry: bool = False) -> dict:
    """Signals before `start` are switched off. With shift_entry the signal is
    moved to the NEXT row (the alert is post-close; the fill is the next open),
    and the EP stop override moves with it."""
    out = {}
    for sym, f in frames.items():
        g = f.copy()
        g.loc[g["date"] < start, "breakout_today"] = False
        if shift_entry:
            g["breakout_today"] = g["breakout_today"].shift(1, fill_value=False).astype(bool)
            if "stop_override" in g.columns:
                g["stop_override"] = g["stop_override"].shift(1)
        out[sym] = g
    return out


def breadth_series(frames: dict) -> pd.Series:
    counts: dict = {}
    above: dict = {}
    for f in frames.values():
        if "sma_200" not in f.columns:
            continue
        sub = f[["date", "close", "sma_200"]].dropna()
        for d, c, s in zip(sub["date"], sub["close"], sub["sma_200"]):
            counts[d] = counts.get(d, 0) + 1
            above[d] = above.get(d, 0) + (1 if c > s else 0)
    s = pd.Series({d: above[d] / counts[d] * 100 for d in counts if counts[d] >= 100})
    return s.sort_index()


def nifty_regime() -> pd.Series:
    b = load_ohlcv("NIFTY50").copy()
    b["sma150"] = b["close"].rolling(150).mean()
    return pd.Series(np.where(b["close"] < b["sma150"], 0.5, 1.0),
                     index=pd.DatetimeIndex(b["date"])).dropna()


# ---------------------------------------------------------------------------
# performance helpers
# ---------------------------------------------------------------------------
def perf(equity: pd.Series, start: pd.Timestamp) -> dict:
    """equity: date-indexed. Measured from `start` (re-based there), so idle
    warm-up years never dilute a CAGR."""
    e = equity[equity.index >= start].astype(float)
    if len(e) < 20:
        return {}
    e = e / e.iloc[0]
    years = (e.index[-1] - e.index[0]).days / 365.25
    cagr = e.iloc[-1] ** (1 / years) - 1 if years > 0 else np.nan
    dd = (e / e.cummax() - 1).min()
    daily = e.pct_change().dropna()
    vol = daily.std() * np.sqrt(252)
    sharpe = ((daily.mean() * 252) - RF_PCT / 100) / vol if vol > 0 else np.nan
    yearly = e.resample("YE").last().pct_change()
    first_year = e.resample("YE").last().iloc[0] / e.iloc[0] - 1
    yearly.iloc[0] = first_year
    return {"cagr_pct": round(cagr * 100, 1), "max_dd_pct": round(dd * 100, 1),
            "mar": round(cagr / abs(dd), 2) if dd < 0 else np.nan,
            "vol_pct": round(vol * 100, 1), "sharpe": round(sharpe, 2),
            "total_x": round(float(e.iloc[-1]), 2),
            "yearly": {str(k.year): round(v * 100, 1) for k, v in yearly.items()}}


# ---------------------------------------------------------------------------
# engine cells
# ---------------------------------------------------------------------------
def run_cell(name, frames, regime, start, results, *, stress=False, ledger_cost=COST_BASE,
             save=True):
    t0 = time.time()
    kw = dict(min_fundamental_score=0.55, starting_cash=STARTING_CASH, rank_by="volume",
              size_on="equity", risk_scale=regime)
    if stress:
        kw.update(entry_price_col="open", stop_fill="gap_aware", entry_day_stop=True)
    if ledger_cost:
        kw.update(cost_pct_per_side=ledger_cost)
    trades, equity = run_backtest(frames, **kw)
    if trades.empty:
        results.append({"config": name, "error": "no trades"})
        return None
    if ledger_cost:
        pnl_col, r_col = "realized_pnl_net", "r_multiple_net"
    else:
        trades = apply_costs(trades)
        pnl_col, r_col = "realized_pnl_after_costs", "r_multiple_after_costs"
    t = trades[trades["entry_date"] >= start]
    # position-level R (both lots of one entry together), the unit a
    # portfolio actually experiences
    pos = (t.assign(risk=t["shares"] * t["risk_per_share"])
             .groupby(["name", "entry_date"])
             .agg(pnl=(pnl_col, "sum"), risk=("risk", "sum"),
                  cls=("entry_class", "first")))
    pos["R"] = pos["pnl"] / pos["risk"]
    eq = equity.set_index(pd.to_datetime(equity["date"]))["equity"]
    p = perf(eq, start)
    lots = trade_stats(t, pnl_col=pnl_col, r_col=r_col)
    r = {"config": name, "positions": len(pos),
         "exp_R_lot": lots.get("expectancy_r"),
         "exp_R_pos": round(float(pos["R"].mean()), 3),
         "median_R_pos": round(float(pos["R"].median()), 3),
         "win_pct_pos": round(float((pos["R"] > 0).mean() * 100), 1),
         "top5_share_pct": round(float(pos["pnl"].nlargest(5).sum() / pos["pnl"].clip(lower=0).sum() * 100), 1)
         if (pos["pnl"] > 0).any() else None,
         **{k: v for k, v in p.items() if k != "yearly"},
         "yearly": p.get("yearly", {}),
         "minutes": round((time.time() - t0) / 60, 1)}
    results.append(r)
    print(f"[{name}] pos={r['positions']} expR(pos)={r['exp_R_pos']} win={r['win_pct_pos']}% "
          f"CAGR={r.get('cagr_pct')}% DD={r.get('max_dd_pct')}% MAR={r.get('mar')} "
          f"Sharpe={r.get('sharpe')} ({r['minutes']}m)", flush=True)
    if save:
        trades.to_csv(os.path.join(ROOT, "matrix_trades", f"HR_{name}.csv"), index=False)
    return eq


# ---------------------------------------------------------------------------
# controls
# ---------------------------------------------------------------------------
def panel(frames: dict, col: str) -> pd.DataFrame:
    return pd.DataFrame({s: f.set_index("date")[col] for s, f in frames.items()}).sort_index()


def _rebalance(holdings: dict, cash: float, target_w: dict, px: pd.Series,
               last_px: dict, cost_pct: float) -> tuple[dict, float, float]:
    """The shared trade mechanics (scoring/momentum.rebalance) — the live
    paper sleeve rebalances with the same function."""
    return momentum.rebalance(holdings, cash, target_w, px, last_px, cost_pct)


def eqw_curve(close: pd.DataFrame, start: pd.Timestamp) -> pd.Series:
    """Equal weight across every name with a price, reset monthly at the
    first session of each month. No costs — it is the opportunity set, not a
    strategy anyone would trade at this turnover."""
    dates = close.index[close.index >= start]
    holdings, cash, last_px, curve = {}, 1.0, {}, []
    cur_month = None
    for d in dates:
        px = close.loc[d]
        m = d.to_period("M")
        if m != cur_month:
            live = [s for s, p in px.items() if pd.notna(p) and p > 0]
            if live:
                w = {s: 1.0 / len(live) for s in live}
                holdings, cash, _ = _rebalance(holdings, cash, w, px, last_px, 0.0)
            cur_month = m
        for s, p in px.items():
            if pd.notna(p) and p > 0:
                last_px[s] = p
        curve.append((d, cash + sum(sh * last_px.get(s, 0) for s, sh in holdings.items())))
    return pd.Series(dict(curve)).sort_index()


def momentum_curve(close: pd.DataFrame, open_: pd.DataFrame, turnover: pd.DataFrame,
                   start: pd.Timestamp, top_n: int = 20, keep_rank: int = 40,
                   cost_pct: float = COST_BASE, regime: pd.Series | None = None,
                   min_turnover_cr: float = 2.0) -> tuple[pd.Series, dict]:
    """Monthly momentum rotation, NSE momentum-index style: score = average of
    the cross-sectional z-scores of (6m return / 1y vol) and (12m return /
    1y vol). Signal at the last session of the month, trades at the next
    session's OPEN. A holding stays until it drops out of the top `keep_rank`
    (a buffer that roughly halves turnover); the target is equal weight.
    `regime` (0.5/1.0, the system's own breadth rule) scales the invested
    fraction; the remainder sits in cash earning nothing."""
    # the SAME scorer the live paper sleeve uses (scoring/momentum.py), so the
    # measured idea and the tracked one cannot drift apart
    pp = momentum.panels(close, turnover)
    dates = close.index[close.index >= start]
    month_end = pd.Series(dates, index=dates).groupby(dates.to_period("M")).last()
    rebal_signal = set(month_end.values[:-1])

    cash, holdings, last_px = 1.0, {}, {}
    curve, traded_sum, n_rebal = [], 0.0, 0
    pending = None
    for i, d in enumerate(dates):
        if pending is not None:
            holdings, cash, traded = _rebalance(holdings, cash, pending, open_.loc[d],
                                                last_px, cost_pct)
            traded_sum += traded
            n_rebal += 1
            pending = None
        for s, p in close.loc[d].items():
            if pd.notna(p) and p > 0:
                last_px[s] = p
        val = cash + sum(sh * last_px.get(s, 0) for s, sh in holdings.items())
        curve.append((d, val))
        if d in rebal_signal and i + 1 < len(dates):
            ranked = momentum.score_at(pp, d, min_turnover_cr)
            if ranked.empty:
                continue
            target = momentum.target_names(ranked, holdings, top_n, keep_rank)
            frac = 1.0
            if regime is not None:
                prior = regime[regime.index <= d]
                frac = float(prior.iloc[-1]) if len(prior) else 1.0
            pending = {s: frac / len(target) for s in target} if target else {}
    eq = pd.Series(dict(curve)).sort_index()
    years = (dates[-1] - dates[0]).days / 365.25
    return eq, {"rebalances": n_rebal,
                "annual_turnover_x": round(traded_sum / max(years, 1e-9) / float(eq.mean()), 2)}


# ---------------------------------------------------------------------------
def main() -> None:
    t_all = time.time()
    uni = pd.read_csv(os.path.join(ROOT, "universe.csv"))
    uni = uni[uni["index_source"] != "nse_gap"]
    cached = set(list_cached())
    syms = [s for s in uni["symbol"] if s in cached]
    print(f"universe: {len(syms)} index names with cached prices", flush=True)

    print("building VCP frames (slow)...", flush=True)
    t0 = time.time()
    vcp, ep = {}, {}
    for i, sym in enumerate(syms, 1):
        df = load_ohlcv(sym)
        if df is None:
            continue
        if len(df) >= MIN_BARS_EP + 5:
            ep[sym] = ep_frame(df)
        if len(df) >= MIN_ROWS_VCP:
            vcp[sym] = generate_signals(df, 0.6)
        if i % 100 == 0:
            print(f"  {i}/{len(syms)} ({time.time() - t0:.0f}s)", flush=True)
    print(f"frames: vcp={len(vcp)} ep={len(ep)} ({(time.time() - t0) / 60:.1f}m)", flush=True)

    breadth = breadth_series(vcp)
    breadth_reg = pd.Series(np.where(breadth < 50, 0.5, 1.0), index=breadth.index)
    nifty_reg = nifty_regime()
    ep_only = {s: f for s, f in ep.items() if f["breakout_today"].any()}
    comb = combine(vcp, ep_only)

    results = []
    curves = {}

    # --- L0: reproduce the published headline (legacy engine, NIFTY regime)
    curves["L0"] = run_cell("L0_repro_2023_nifty_gross", windowed(comb, EP_WINDOW), nifty_reg,
                            EP_WINDOW, results, ledger_cost=0.0)
    # --- the live configuration, 2023-08 window
    curves["L1"] = run_cell("L1_live_2023_breadth_net", windowed(comb, EP_WINDOW), breadth_reg,
                            EP_WINDOW, results)
    curves["L2"] = run_cell("L2_live_2023_stress", windowed(comb, EP_WINDOW, shift_entry=True),
                            breadth_reg, EP_WINDOW, results, stress=True, ledger_cost=COST_STRESS)
    # --- the live configuration, full window
    curves["F1"] = run_cell("F1_live_full_net", windowed(comb, FULL_WINDOW), breadth_reg,
                            FULL_WINDOW, results)
    curves["F2"] = run_cell("F2_live_full_stress", windowed(comb, FULL_WINDOW, shift_entry=True),
                            breadth_reg, FULL_WINDOW, results, stress=True, ledger_cost=COST_STRESS)
    # --- the two entry classes alone, full window (which one carries it?)
    curves["F3"] = run_cell("F3_vcp_only_full_net", windowed(vcp, FULL_WINDOW), breadth_reg,
                            FULL_WINDOW, results)
    curves["F4"] = run_cell("F4_ep_only_full_net", windowed(ep_only, FULL_WINDOW), breadth_reg,
                            FULL_WINDOW, results)

    # --- controls on the same universe
    print("building price panels for the controls...", flush=True)
    close = panel(ep, "close")
    open_ = panel(ep, "open")
    vol = panel(ep, "volume")
    turnover = close * vol
    for label, start in (("full", FULL_WINDOW), ("2023", EP_WINDOW)):
        c_eqw = eqw_curve(close, start)
        curves[f"EQW_{label}"] = c_eqw
        m_eq, m_info = momentum_curve(close, open_, turnover, start)
        curves[f"MOM_{label}"] = m_eq
        mr_eq, mr_info = momentum_curve(close, open_, turnover, start, regime=breadth_reg)
        curves[f"MOMR_{label}"] = mr_eq
        for nm, eq, info in ((f"EQW_{label}", c_eqw, {}), (f"MOM_{label}", m_eq, m_info),
                             (f"MOMR_{label}", mr_eq, mr_info)):
            p = perf(eq, start)
            results.append({"config": nm, **{k: v for k, v in p.items() if k != "yearly"},
                            "yearly": p.get("yearly", {}), **info})
            print(f"[{nm}] CAGR={p.get('cagr_pct')}% DD={p.get('max_dd_pct')}% MAR={p.get('mar')} "
                  f"Sharpe={p.get('sharpe')} {info}", flush=True)
    for bsym in ("NIFTY50", "MOMENTUM100"):
        b = load_ohlcv(bsym)
        if b is None:
            continue
        s = b.set_index("date")["close"]
        for label, start in (("full", FULL_WINDOW), ("2023", EP_WINDOW)):
            p = perf(s, start)
            results.append({"config": f"{bsym}_{label}", **{k: v for k, v in p.items() if k != "yearly"},
                            "yearly": p.get("yearly", {})})

    # --- report
    out_json = os.path.join(ROOT, "honest_rerun_results.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=1, default=str)
    cols = ["config", "positions", "exp_R_pos", "median_R_pos", "win_pct_pos", "top5_share_pct",
            "cagr_pct", "max_dd_pct", "mar", "sharpe", "vol_pct", "total_x"]
    lines = ["# Honest re-run — the live strategy on the corrected engine (2026-09-25)", "",
             "Research diagnostic. No live rule changed. See the module docstring of",
             "`scripts/run_honest_rerun.py` for what each row is and why it exists.", "",
             "| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for r in results:
        lines.append("| " + " | ".join(str(r.get(c, "")) for c in cols) + " |")
    lines += ["", "## Calendar-year returns (%)", ""]
    years = sorted({y for r in results for y in (r.get("yearly") or {})})
    lines.append("| config | " + " | ".join(years) + " |")
    lines.append("|" + "---|" * (len(years) + 1))
    for r in results:
        yr = r.get("yearly") or {}
        lines.append(f"| {r['config']} | " + " | ".join(str(yr.get(y, "")) for y in years) + " |")
    with open(os.path.join(ROOT, "honest_rerun_report.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    pd.DataFrame({k: v for k, v in curves.items() if v is not None}).to_csv(
        os.path.join(ROOT, "matrix_trades", "HR_equity_curves.csv"))
    print(f"\ndone in {(time.time() - t_all) / 60:.1f}m -> honest_rerun_report.md", flush=True)


if __name__ == "__main__":
    main()
