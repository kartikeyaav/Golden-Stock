"""
research/sim.py — a portfolio simulator for multibagger strategies on the
survivorship-free grids (PREREG_2026-09-26 §5).

Deliberately different from backtest/engine.py: that engine is the two-lot
VCP/EP plan (partial at 2.5R, breakeven, 50-day trail). A multibagger strategy
has to be able to HOLD — months to years — so exits here are trend exits only
(no profit target), and concentration is a parameter.

Mechanics, all known at the time:
  * signal at t's close -> buy at t+1's open ("open"), or at t's close ("close",
    the 3:10 PM workflow — scripts/breakout_watch.py measured a 15:20 fill at a
    median 0.00% from the official close);
  * equal-weight slots: each new position gets equity / max_positions, capped
    at `liq_cap` x its 20-day median traded value (a small-cap order the market
    cannot absorb is not filled at the screen price);
  * costs per side on every fill;
  * exits evaluated on closes, filled at the next open:
      - initial stop: close <= entry x (1 - stop_pct)
      - trend exit (after `min_hold` sessions): close < SMA(trail) — or a
        chandelier stop (highest close since entry - k x ATR)
  * a LOWER-CIRCUIT LOCK: a stock whose session printed high == low below the
    prior close could not be sold that day; the exit waits for a tradable day.
  * breadth exposure (optional): a daily series in [0, 1] that scales the size
    of NEW positions (the system's regime rule); existing positions are held.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from research.grid import Grid, roll, shift


@dataclass
class SimConfig:
    max_positions: int = 10
    fill: str = "open"               # "open" (next session) | "close" (signal day)
    cost_pct: float = 0.25           # per side, % of traded value
    stop_pct: float = 0.20           # initial stop, fraction below entry
    exit: str = "sma"                # "sma" | "chandelier"
    trail: int = 50                  # SMA period for the trend exit
    chandelier_k: float = 3.0
    min_hold: int = 20               # sessions before the trend exit is armed
    liq_cap: float = 0.05            # max position = 5% of 20-day median traded value
    start_cash: float = 1e6


def run(g: Grid, signal: np.ndarray, rank: np.ndarray | None, cfg: SimConfig,
        start: pd.Timestamp, end: pd.Timestamp | None = None,
        exposure: np.ndarray | None = None, risk_on: np.ndarray | None = None) -> dict:
    """signal: bool (T x N) at t's close. rank: float (T x N), higher = preferred
    when more names signal than slots are free (None = traded value).
    risk_on: bool (T,) — the REGIME EXIT (PREREG amendment 2026-09-26): on a
    close where it is False every position is sold at the next open and no
    entry is taken until it is True again."""
    T, N = g.T, g.N
    t0 = int(np.searchsorted(g.dates.values, np.datetime64(start)))
    t1 = T if end is None else int(np.searchsorted(g.dates.values, np.datetime64(end), side="right"))
    c, o, h, l = g.c, g.o, g.h, g.l
    prev_c = shift(c, 1)
    locked = (h <= l) & (c < prev_c)                         # limit-down, no range
    if cfg.exit == "sma":
        trail = g.sma(cfg.trail)
    else:
        tr = np.fmax(h - l, np.fmax(np.abs(h - prev_c), np.abs(l - prev_c)))
        atr = roll(tr, 14, "mean", minp=10)
    medtv = roll(g.tv, 20, "median", minp=10)
    if rank is None:
        rank = medtv
    cash = cfg.start_cash
    pos: dict[int, dict] = {}                                # j -> position
    pending_buys: list[int] = []
    pending_sells: list[int] = []
    eq_curve, trades = [], []
    last_px = np.full(N, np.nan, dtype="float64")

    for t in range(t0, t1):
        # ---- fills at today's open (decided at yesterday's close) --------------
        for j in list(pending_sells):
            if j not in pos:
                pending_sells.remove(j)
                continue
            if locked[t, j] or not np.isfinite(o[t, j]):
                continue                                     # cannot sell today; try again
            p = pos.pop(j)
            px = float(o[t, j])
            cash += p["sh"] * px * (1 - cfg.cost_pct / 100)
            trades.append({**p, "exit_t": t, "exit_px": px, "mult": px / p["px"]})
            pending_sells.remove(j)
        if cfg.fill == "open":
            cash_ref = [cash]
            for j in pending_buys:
                if len(pos) >= cfg.max_positions:
                    break                                    # a stuck sale still holds its slot
                px = float(o[t, j]) if np.isfinite(o[t, j]) else np.nan
                _buy(j, t, t - 1, px, pos, cfg, medtv, exposure, cash_ref)
            cash = cash_ref[0]
            pending_buys = []

        # ---- mark to market ----------------------------------------------------
        row = c[t]
        ok = np.isfinite(row)
        last_px[ok] = row[ok]
        val = cash + sum(p["sh"] * last_px[j] for j, p in pos.items() if np.isfinite(last_px[j]))
        eq_curve.append((g.dates[t], val))

        # ---- the regime exit: risk off -> everything out at the next open --------
        if risk_on is not None and not bool(risk_on[t]):
            for j in pos:
                if j not in pending_sells:
                    pending_sells.append(j)
            pending_buys = []
            continue
        # ---- exits decided at today's close ---------------------------------------
        for j, p in pos.items():
            cj = c[t, j]
            if not np.isfinite(cj):
                continue
            p["peak"] = max(p["peak"], float(cj))
            held = t - p["entry_t"]
            out = cj <= p["px"] * (1 - cfg.stop_pct)
            if not out and held >= cfg.min_hold:
                if cfg.exit == "sma":
                    tj = trail[t, j]
                    out = np.isfinite(tj) and cj < tj
                else:
                    a = atr[t, j]
                    out = np.isfinite(a) and cj < p["peak"] - cfg.chandelier_k * a
            if out and j not in pending_sells:
                pending_sells.append(j)

        # ---- entries decided at today's close ------------------------------------
        free = cfg.max_positions - len(pos) + len(pending_sells)
        if free > 0 and t + 1 < t1:
            cand = np.nonzero(signal[t] & np.isfinite(c[t]))[0]
            cand = [j for j in cand if j not in pos]
            if cand:
                r = rank[t, cand]
                order = [cand[k] for k in np.argsort(-np.nan_to_num(r, nan=-np.inf))]
                chosen = order[:free]
                if cfg.fill == "close":
                    cash_ref = [cash]
                    for j in chosen:
                        if len(pos) >= cfg.max_positions:
                            break
                        _buy(j, t, t, float(c[t, j]), pos, cfg, medtv, exposure, cash_ref)
                    cash = cash_ref[0]
                else:
                    pending_buys = chosen

    # close the book at the end (marked, not sold)
    for j, p in pos.items():
        px = last_px[j]
        trades.append({**p, "exit_t": None, "exit_px": float(px), "mult": float(px) / p["px"],
                       "open": True})
    eq = pd.Series(dict(eq_curve)).sort_index()
    return {"equity": eq, "trades": pd.DataFrame(trades)}


def _buy(j, t, t_decide, px, pos, cfg, medtv, exposure, cash_ref):
    """Fill one entry at `px` on session t, sized with what was known at
    `t_decide` (the signal session). cash_ref is a one-item list so a batch of
    buys draws down the SAME cash."""
    if not np.isfinite(px) or px <= 0 or j in pos:
        return
    cash = cash_ref[0]
    # equity is approximated by cash + position cost basis (mark-to-market is
    # applied daily in the curve; sizing on it avoids a second full valuation)
    equity = cash + sum(p["sh"] * p["px"] for p in pos.values())
    alloc = equity / cfg.max_positions
    if exposure is not None:
        x = exposure[t_decide]
        alloc *= float(x) if np.isfinite(x) else 0.5            # unknown regime = half (AUDIT F9)
    cap = cfg.liq_cap * float(medtv[t_decide, j]) if np.isfinite(medtv[t_decide, j]) else 0.0
    alloc = min(alloc, cap, cash / (1 + cfg.cost_pct / 100))
    sh = int(alloc // px)
    if sh <= 0:
        return
    cash -= sh * px * (1 + cfg.cost_pct / 100)
    pos[j] = {"j": j, "entry_t": t, "px": px, "sh": sh, "peak": px}
    cash_ref[0] = cash


def perf(eq: pd.Series) -> dict:
    e = eq.dropna()
    if len(e) < 20:
        return {}
    e = e / e.iloc[0]
    yrs = (e.index[-1] - e.index[0]).days / 365.25
    cagr = e.iloc[-1] ** (1 / yrs) - 1
    dd = (e / e.cummax() - 1).min()
    d = e.pct_change().dropna()
    sharpe = (d.mean() * 252 - 0.065) / (d.std() * np.sqrt(252)) if d.std() > 0 else np.nan
    yearly = e.resample("YE").last()
    yr = yearly.pct_change()
    yr.iloc[0] = yearly.iloc[0] / e.iloc[0] - 1
    return {"cagr_pct": round(cagr * 100, 1), "max_dd_pct": round(dd * 100, 1),
            "mar": round(cagr / abs(dd), 2) if dd < 0 else None, "sharpe": round(sharpe, 2),
            "total_x": round(float(e.iloc[-1]), 1),
            "yearly": {str(k.year): round(v * 100, 1) for k, v in yr.items()}}
