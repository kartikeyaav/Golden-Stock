"""
scripts/run_pit_rerun.py — the honest re-run, without survivorship bias.

GAP 2 (REVIEW_2026-09-25). Every earlier number — including the "honest" 45% /
30% — ran on today's index members, and owning that list blindly returned 33% a
year since 2020 against 21% for the real Midcap-100 ETF. This re-runs the SAME
cells as scripts/run_honest_rerun.py (same engine, same signal construction,
same costs, same breadth rule) on the universe as it stood on each date:

  * prices: every NSE equity, every session, 2005 -> today, from the exchange's
    bhavcopies (data/nse_history.py) — names that later crashed, were
    suspended or delisted stay in;
  * universe on date t: stocks ranked 101-750 by 60-day median traded value
    among EQ/BE/BZ names with >= 250 sessions of history — the rank band the
    Midcap 150 + Smallcap 250 + Microcap 250 cover by market cap, built only
    from data known at t. A signal on a date the stock was not in that band is
    switched off. (Traded value is the only size measure the exchange files
    carry; it is the proxy, and it is stated as one.)

Windows: 2006-01 (twenty years, both bear markets) and 2020-01 (the window the
biased re-run reported, for a like-for-like comparison).

    python scripts/run_pit_rerun.py [--workers 12] [--window both|2006|2020]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from data.nse_history import load_panel  # noqa: E402

RANK_LO, RANK_HI = 101, 750
MIN_HISTORY = 250
WINDOWS = {"2006": pd.Timestamp("2006-01-02"), "2020": pd.Timestamp("2020-01-01")}
KEEP = ["date", "open", "high", "low", "close", "volume", "atr", "avg_vol_50", "is_week_end",
        "breakout_today", "stop_override", "fundamental_score"]
OUT = os.path.join(ROOT, "research", "out")


def pit_universe(p) -> pd.DataFrame:
    """bool frame (dates x symbols): in the 101-750 traded-value band on t."""
    tv = pd.DataFrame(p.turnover, index=p.dates, columns=p.symbols)
    med = tv.rolling(60, min_periods=30).median()
    listed = pd.DataFrame(np.isin(p.series, (1, 2, 3)), index=p.dates, columns=p.symbols)
    hist = pd.DataFrame(np.cumsum(~np.isnan(p.close), axis=0) >= MIN_HISTORY,
                        index=p.dates, columns=p.symbols)
    elig = listed & hist & med.notna()
    rank = med.where(elig).rank(axis=1, ascending=False, method="first")
    return (rank >= RANK_LO) & (rank <= RANK_HI)


def _frames_for(args):
    """worker: ONE frame per company carrying both signal families as flags
    (vcp_bo, ep_bo, ep_stop), trimmed to what the engine reads, float32.
    One frame instead of two, and each cell rewrites breakout_today in place
    (set_cell) — copying ~2,500 twenty-year frames per cell does not fit."""
    sym, df = args
    from backtest.engine import generate_signals
    from run_honest_rerun import ep_frame, MIN_BARS_EP, MIN_ROWS_VCP
    try:
        e = ep_frame(df) if len(df) >= MIN_BARS_EP + 5 else None
        v = generate_signals(df, 0.6) if len(df) >= MIN_ROWS_VCP else None
    except Exception as ex:  # noqa: BLE001
        return sym, {"error": f"{type(ex).__name__}: {ex}"[:200]}
    base = v if v is not None else e
    if base is None:
        return sym, {}
    f = base[[c for c in base.columns if c in KEEP or c.startswith("sma_")]].copy()
    f["vcp_bo"] = v["breakout_today"].astype(bool).to_numpy() if v is not None else False
    if e is not None:
        f["ep_bo"] = e["breakout_today"].astype(bool).to_numpy()
        f["ep_stop"] = e["stop_override"].to_numpy()
    else:
        f["ep_bo"] = False
        f["ep_stop"] = np.nan
    f = f.drop(columns=[c for c in ("breakout_today", "stop_override") if c in f.columns])
    for c in f.columns:
        if f[c].dtype == "float64":
            f[c] = f[c].astype("float32")
    return sym, {"frame": f}


def set_cell(frames: dict, kind: str, start: pd.Timestamp, shift_entry: bool = False) -> dict:
    """Rewrite breakout_today / stop_override IN PLACE for one cell, exactly as
    run_honest_rerun.combine + windowed would build them: VCP's own stop where
    VCP fires, the EP stop where only EP fires; nothing before `start`; with
    shift_entry the flag (and the EP stop) move to the next row = next-open fill.
    Returns the dict of frames that can trade in this cell."""
    live = {}
    for s, f in frames.items():
        v, e = f["vcp_bo"].to_numpy(), f["ep_bo"].to_numpy()
        if kind == "vcp":
            bo, stop = v, np.full(len(f), np.nan, dtype="float32")
        elif kind == "ep":
            bo, stop = e, np.where(e, f["ep_stop"].to_numpy(), np.nan)
        else:
            bo = v | e
            stop = np.where(e & ~v, f["ep_stop"].to_numpy(), np.nan)
        bo = bo & (f["date"].to_numpy() >= np.datetime64(start))
        if shift_entry:
            bo = np.concatenate([[False], bo[:-1]])
            stop = np.concatenate([[np.nan], stop[:-1]])
        f["breakout_today"] = bo
        f["stop_override"] = stop.astype("float32")
        if kind == "ep" and not e.any():
            continue
        live[s] = f
    return live


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--window", default="both")
    a = ap.parse_args()
    t_all = time.time()
    import run_honest_rerun as HR   # the same cells, the same mechanics

    p = load_panel()
    U = pit_universe(p)
    first = min(WINDOWS.values()) - pd.Timedelta(days=500)
    ever = U.loc[U.index >= min(WINDOWS.values())].any(axis=0)
    syms = [s for s in p.symbols if ever.get(s, False)]
    print(f"panel {len(p.dates)} x {len(p.symbols)}; ever in the 101-750 band since "
          f"{min(WINDOWS.values()).date()}: {len(syms)} companies", flush=True)

    rows = p.dates >= first
    U = U.loc[p.dates[rows]]
    adj = p.adj[rows]
    O, Hh, L, C = (p.open[rows] * adj, p.high[rows] * adj, p.low[rows] * adj, p.close[rows] * adj)
    V = p.volume[rows] / adj
    dates = p.dates[rows]
    TV_raw = p.turnover[rows].copy()
    symbols = list(p.symbols)
    jobs = []
    for s in syms:
        j = p.col[s]
        m = ~np.isnan(C[:, j])
        if m.sum() < 60:
            continue
        df = pd.DataFrame({"date": dates[m], "open": O[m, j], "high": Hh[m, j], "low": L[m, j],
                           "close": C[m, j], "volume": V[m, j]}).astype(
            {"open": "float64", "high": "float64", "low": "float64", "close": "float64",
             "volume": "float64"})
        df["open"] = df["open"].fillna(df["close"])
        df["high"] = df[["high", "close"]].max(axis=1)
        df["low"] = df[["low", "close"]].min(axis=1)
        jobs.append((s, df.reset_index(drop=True)))
    # the raw panel and the grids only the frames needed are released before
    # the workers start: ~1 GB back on a machine with ~3 GB free
    del Hh, L, V, adj
    del p
    import gc
    gc.collect()
    print(f"building signal frames for {len(jobs)} companies on {a.workers} workers...", flush=True)
    t0 = time.time()
    frames, errs = {}, 0
    with ProcessPoolExecutor(max_workers=a.workers) as ex:
        for i, (s, out) in enumerate(ex.map(_frames_for, jobs, chunksize=4), 1):
            if "error" in out:
                errs += 1
            elif "frame" in out:
                f = out["frame"]
                # point-in-time eligibility: a signal only counts on a date the
                # stock was inside the band
                inU = U[s].reindex(pd.DatetimeIndex(f["date"])).fillna(False).to_numpy()
                f["vcp_bo"] = f["vcp_bo"].to_numpy() & inU
                f["ep_bo"] = f["ep_bo"].to_numpy() & inU
                frames[s] = f
            if i % 250 == 0:
                print(f"  {i}/{len(jobs)} ({(time.time() - t0) / 60:.1f}m)", flush=True)
    del jobs
    n_v = sum(int(f["vcp_bo"].sum()) for f in frames.values())
    n_e = sum(int(f["ep_bo"].sum()) for f in frames.values())
    print(f"frames: {len(frames)} companies, errors={errs}; in-band signals VCP {n_v:,} EP {n_e:,} "
          f"({(time.time() - t0) / 60:.1f}m)", flush=True)

    # the breadth rule over the SAME universe: % of band members above their 200-day average
    Cf = pd.DataFrame(C, index=dates, columns=symbols)
    sma200 = Cf.rolling(200, min_periods=200).mean()
    Ub = U.loc[dates]
    above = (Cf > sma200) & Ub & sma200.notna()
    breadth = (above.sum(axis=1) / (Ub & sma200.notna()).sum(axis=1).replace(0, np.nan) * 100)
    breadth_reg = pd.Series(np.where(breadth < 50, 0.5, 1.0), index=dates)
    breadth_reg[breadth.isna()] = 0.5                    # unknown = defensive (AUDIT F9)

    results, curves = [], {}
    wins = WINDOWS if a.window == "both" else {a.window: WINDOWS[a.window]}
    cells = [("F1_live", "comb", False, False), ("F2_live_stress", "comb", True, True),
             ("F3_vcp_only", "vcp", False, False), ("F4_ep_only", "ep", False, False)]
    for label, start in wins.items():
        # the 2020 window repeats all four cells of the biased re-run (like for
        # like); the 20-year window runs the live configuration only (ideal and
        # realistic fills) — each 20-year cell is ~3x the engine time
        for name, kind, shifted, stress in (cells if label == "2020" else cells[:2]):
            live = set_cell(frames, kind, start, shift_entry=shifted)
            kw = dict(stress=True, ledger_cost=HR.COST_STRESS) if stress else {}
            curves[f"PIT_{name}_{label}"] = HR.run_cell(f"PIT_{name}_{label}", live, breadth_reg,
                                                        start, results, save=False, **kw)

    # controls on the same point-in-time universe
    Of = pd.DataFrame(O, index=dates, columns=symbols)
    TV = pd.DataFrame(TV_raw, index=dates, columns=symbols)
    from scoring import momentum
    for label, start in wins.items():
        # equal weight of the band, reset monthly (first session), survivors AND casualties
        eqw = eqw_pit(Cf, Ub, start)
        curves[f"PIT_EQW_{label}"] = eqw
        # momentum rotation restricted to band members (turnover masked outside the band)
        pp = momentum.panels(Cf, TV)
        pp["med_to"] = pp["med_to"].where(Ub)
        orig = momentum.panels
        try:
            momentum.panels = lambda close, turnover, _pp=pp: _pp
            mr, info = HR.momentum_curve(Cf, Of, TV, start, regime=breadth_reg)
        finally:
            momentum.panels = orig
        curves[f"PIT_MOMR_{label}"] = mr
        for nm, eq, inf in ((f"PIT_EQW_{label}", eqw, {}), (f"PIT_MOMR_{label}", mr, info)):
            pf = HR.perf(eq, start)
            results.append({"config": nm, **{k: v for k, v in pf.items() if k != "yearly"},
                            "yearly": pf.get("yearly", {}), **inf})
            print(f"[{nm}] CAGR={pf.get('cagr_pct')}% DD={pf.get('max_dd_pct')}% "
                  f"MAR={pf.get('mar')} Sharpe={pf.get('sharpe')} {inf}", flush=True)
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "pit_rerun_results.json"), "w", encoding="utf-8") as f:
        json.dump({"universe": f"traded-value rank {RANK_LO}-{RANK_HI}, >= {MIN_HISTORY} sessions",
                   "results": results}, f, indent=1, default=str)
    pd.DataFrame({k: v for k, v in curves.items() if v is not None}).to_csv(
        os.path.join(OUT, "pit_rerun_curves.csv.gz"))
    print(f"done in {(time.time() - t_all) / 60:.1f}m", flush=True)
    return 0


def eqw_pit(C: pd.DataFrame, U: pd.DataFrame, start: pd.Timestamp) -> pd.Series:
    """Equal weight of the band's members, reset at each month's first session.
    A member that stops trading keeps its last price for the rest of the month
    (it does not vanish), and leaves at the next reset."""
    C = C.loc[C.index >= start - pd.Timedelta(days=40)]
    U = U.loc[C.index]
    cf = C.ffill()
    months = C.index.to_period("M")
    firsts = pd.Series(C.index, index=C.index).groupby(months).first()
    val, out = 1.0, {}
    firsts = firsts[firsts >= start]
    for k, d0 in enumerate(firsts):
        d1 = firsts.iloc[k + 1] if k + 1 < len(firsts) else C.index[-1]
        members = U.loc[:d0].iloc[-2] if len(U.loc[:d0]) >= 2 else U.loc[d0]
        names = members[members].index
        base = cf.loc[d0, names]
        names = base[base > 0].index
        seg = cf.loc[d0:d1, names].div(cf.loc[d0, names])
        path = seg.mean(axis=1) * val
        for d, x in path.items():
            out[d] = x
        val = float(path.iloc[-1])
    return pd.Series(out).sort_index()


if __name__ == "__main__":
    raise SystemExit(main())
