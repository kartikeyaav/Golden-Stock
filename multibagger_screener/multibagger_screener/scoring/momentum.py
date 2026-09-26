"""
scoring/momentum.py — the momentum-core ranking (PREREG_2026-09-25_momentum_core.md).

ONE implementation, used by both the backtest that measured the idea
(scripts/run_honest_rerun.momentum_curve) and the live paper sleeve
(scripts/momentum_core.py), so the thing tracked forward is exactly the thing
that was measured — the drift this project keeps finding between a validated
design and its live copy cannot happen here.

The score is the NSE momentum-index construction: for every stock, the
6-month and the 12-month price return, each divided by the stock's 1-year
annualised volatility of daily log returns; each of the two is z-scored
across the universe on the signal date, and the score is their average.
Volatility-adjusting stops the ranking from being a list of the wildest
movers. A liquidity floor keeps names out whose median daily traded value is
too thin to enter and exit a sleeve-sized position.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

LOOKBACK_6M = 126
LOOKBACK_12M = 252
VOL_WINDOW = 252
VOL_MIN_PERIODS = 200
TURNOVER_WINDOW = 60
TURNOVER_MIN_PERIODS = 40
MIN_TURNOVER_CR = 2.0          # median daily traded value floor, Rs crore
TOP_N = 20                     # names held
KEEP_RANK = 40                 # a holding stays until it falls below this rank


def panels(close: pd.DataFrame, turnover: pd.DataFrame) -> dict:
    """Precompute the rolling inputs once for a date x symbol close panel."""
    logret = np.log(close / close.shift(1))
    vol1y = logret.rolling(VOL_WINDOW, min_periods=VOL_MIN_PERIODS).std() * np.sqrt(252)
    return {
        "vol1y": vol1y,
        "r6": close / close.shift(LOOKBACK_6M) - 1,
        "r12": close / close.shift(LOOKBACK_12M) - 1,
        "med_to": turnover.rolling(TURNOVER_WINDOW, min_periods=TURNOVER_MIN_PERIODS).median(),
    }


def score_at(pp: dict, date, min_turnover_cr: float = MIN_TURNOVER_CR) -> pd.Series:
    """Momentum score of every eligible name on `date`, highest first.
    Empty when too few names qualify to rank (fewer than 2 x TOP_N)."""
    v = pp["vol1y"].loc[date]
    a = pp["r6"].loc[date] / v
    b = pp["r12"].loc[date] / v
    ok = (pp["med_to"].loc[date] >= min_turnover_cr * 1e7) & v.notna() & a.notna() & b.notna()
    a, b = a[ok], b[ok]
    if len(a) < TOP_N * 2:
        return pd.Series(dtype=float)
    z = ((a - a.mean()) / a.std() + (b - b.mean()) / b.std()) / 2
    return z.sort_values(ascending=False)


def breadth_at(close: pd.DataFrame, date, min_rows: int = 300, min_names: int = 100) -> float | None:
    """% of names closing above their own 200-day average on `date` — the
    system's regime rule, over the same names the backtest counted (those
    with at least `min_rows` bars of history)."""
    hist = close.loc[:date]
    enough = hist.notna().sum() >= min_rows
    sub = hist.loc[:, enough]
    sma = sub.rolling(200).mean().iloc[-1]
    last = sub.iloc[-1]
    ok = sma.notna() & last.notna()
    if ok.sum() < min_names:
        return None
    return float((last[ok] > sma[ok]).mean() * 100)


def rebalance(holdings: dict, cash: float, target_w: dict, px: pd.Series,
              last_px: dict, cost_pct: float, fills: list | None = None) -> tuple[dict, float, float]:
    """Trade `holdings` (symbol -> shares) to target weights at prices `px`
    (fallback: last known close). Sells first so buys can be funded; costs are
    charged on the traded value of every buy and sell. Returns (holdings,
    cash, traded_value). When `fills` is a list, one record per trade is
    appended to it — the live sleeve's ledger; the backtest passes None."""
    def price(s):
        p = px.get(s)
        return p if pd.notna(p) and p > 0 else last_px.get(s)
    val = cash + sum(sh * (price(s) or 0) for s, sh in holdings.items())
    traded = 0.0
    for s in list(holdings):
        p = price(s)
        if p is None:
            continue
        want = target_w.get(s, 0.0) * val
        have = holdings[s] * p
        if have > want + 1e-12:
            sell_val = have - want
            cash += sell_val * (1 - cost_pct / 100)
            traded += sell_val
            new_sh = want / p
            if fills is not None:
                fills.append({"symbol": s, "action": "SELL" if new_sh <= 1e-12 else "TRIM",
                              "shares": round(holdings[s] - new_sh, 4), "price": round(float(p), 2),
                              "value": round(sell_val, 2), "cost": round(sell_val * cost_pct / 100, 2)})
            holdings[s] = new_sh
            if holdings[s] <= 1e-12:
                del holdings[s]
    for s, w in target_w.items():
        p = price(s)
        if p is None:
            continue
        want = w * val
        have = holdings.get(s, 0.0) * p
        if want > have + 1e-12:
            spend = min(want - have, cash)
            if spend <= 0:
                continue
            add = spend * (1 - cost_pct / 100) / p
            if fills is not None:
                fills.append({"symbol": s, "action": "BUY" if s not in holdings else "ADD",
                              "shares": round(add, 4), "price": round(float(p), 2),
                              "value": round(spend, 2), "cost": round(spend * cost_pct / 100, 2)})
            holdings[s] = holdings.get(s, 0.0) + add
            cash -= spend
            traded += spend
    return holdings, cash, traded


def target_names(ranked: pd.Series, holdings, top_n: int = TOP_N,
                 keep_rank: int = KEEP_RANK) -> list[str]:
    """Keep every current holding still ranked within `keep_rank`, then fill
    to `top_n` from the top of the ranking. The buffer roughly halves turnover
    against a strict top-N rebuild."""
    if ranked.empty:
        return []
    rank = pd.Series(np.arange(1, len(ranked) + 1), index=ranked.index)
    keep = [s for s in holdings if s in rank.index and rank[s] <= keep_rank]
    new = [s for s in ranked.index if s not in keep][: max(0, top_n - len(keep))]
    return keep + new
