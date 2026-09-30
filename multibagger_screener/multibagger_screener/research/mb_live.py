"""
research/mb_live.py — the rebuilt multibagger score, computed nightly by the
radar on the whole-market panel, with one line of evidence per factor.

The flags come from the RESEARCH functions (research/factor_study.factors,
q_grid; research/insider_study.h25_grid) and the weights from
research/mb_score.config(), on the committed live tables:
  value_fundamentals.csv   annual statements (weekly, rolling)
  shareholding.csv         yearly and quarterly shareholding (weekly)
  quarterly_results.csv    the last 13 quarters (weekly)
  insider_archive.csv      promoter / director / KMP trades (nightly)
The timings are the tested ones: fiscal year Y from 1 October Y, the March
shareholding from 1 May, a quarter 45 days after it ends.
"""

from __future__ import annotations

import os

import numpy as np
import pandas as pd

from research import mb_score

FIELDS = ("sales", "op", "np", "cfo", "cfi", "eq", "borrow", "assets", "roce")
Q1_NAME = "Q1 quarterly: profit +25%, sales +20% on the same quarter last year"


def _read(path: str) -> pd.DataFrame:
    try:
        return pd.read_csv(path)
    except (OSError, ValueError):
        return pd.DataFrame()


def tables(root: str) -> dict[str, pd.DataFrame]:
    vt = _read(os.path.join(root, "value_fundamentals.csv"))
    for c in FIELDS:
        if c not in vt.columns:
            vt[c] = np.nan
    sh = _read(os.path.join(root, "shareholding.csv"))
    if len(sh):
        sh = sh[(sh["kind"] == "yearly") & sh["period"].astype(str).str.endswith("-03")].copy()
        sh["yr"] = sh["period"].astype(str).str[:4].astype(int)
    q = _read(os.path.join(root, "quarterly_results.csv"))
    if len(q):
        q = q.rename(columns={"sales": "rev", "np": "pat"})
        q["known"] = (pd.to_datetime(q["qend"]) + pd.Timedelta(days=45)).dt.strftime("%Y-%m-%d")
        q["src"] = 1
        q = q.dropna(subset=["rev", "pat"])
    return {"annual": vt, "shareholding": sh, "quarterly": q}


def _f(v, fmt="{:,.0f}"):
    return fmt.format(v) if v is not None and np.isfinite(v) else "?"


def live(g, root: str, trades: pd.DataFrame | None = None) -> dict:
    """Every liquid name with at least one surviving factor: a name left out
    of the list would read as a score of 0 on its stock page."""
    from research.factor_study import dated_grids, factors, mcap_grid, q_grid
    from research.grid import roll
    from research.insider_study import grid_of, h25_grid, promoter_purchases, signal_rows
    T = tables(root)
    fy = dated_grids(g, T["annual"], "fy", FIELDS, "10-01", backs=(0, 1))
    sh = (dated_grids(g, T["shareholding"], "yr", ("prom", "fii", "dii", "nsh"), "05-01", backs=(0, 1)) if len(T["shareholding"])
          else {f"{k}{s}": np.full((g.T, g.N), np.nan, "float32") for k in ("prom", "fii", "dii", "nsh") for s in ("", "_1")})
    mc = mcap_grid(g, T["annual"])
    tr = trades if trades is not None else pd.DataFrame(columns=["symbol", "category", "txn", "mode", "value", "disclosed_at"])
    promo = grid_of(g, signal_rows(g, promoter_purchases(tr))) if len(tr) else np.zeros((g.T, g.N), bool)
    promo60 = roll(promo.astype("float32"), 60, "max", minp=1) > 0
    flags = factors(g, fy, sh, mc, promo60)
    flags[Q1_NAME] = q_grid(g, T["quarterly"]) if len(T["quarterly"]) else np.zeros((g.T, g.N), bool)
    flags[mb_score.H25_KEY] = h25_grid(g, tr) if len(tr) else np.zeros((g.T, g.N), bool)
    cfg = mb_score.config()
    sc = mb_score.score(flags, cfg)
    t, U = g.T - 1, g.universe()
    ev = _evidence_fn(g, t, fy, sh, mc, T, tr)
    stocks = {}
    for j in np.nonzero(U[t] & (sc[t] > 0))[0]:
        names = [n for n in cfg if flags[n][t, j]]
        sym = g.symbols[j].split("~")[0]
        stocks[sym] = {"score": round(float(sc[t, j]), 1), "factors": names, "evidence": {n: ev(n, j, sym) for n in names},
                       "close": round(float(g.c_raw[t, j]), 2)}
    ranked = dict(sorted(stocks.items(), key=lambda kv: -kv[1]["score"]))
    return {"asof": str(g.dates[t].date()), "config": cfg, "stocks": ranked,
            "scored": int((U[t] & (sc[t] > 0)).sum()), "universe": int(U[t].sum())}


def _evidence_fn(g, t, fy, sh, mc, T, tr):
    """One line of evidence per factor, from the same point-in-time grids."""
    def at(a, j):
        v = a[t, j]
        return float(v) if np.isfinite(v) else None

    def ch(a, b):
        return (a / b - 1) * 100 if a is not None and b not in (None, 0) else None

    def evid(name: str, j: int, sym: str) -> str:
        k = name[:2]
        s0, s1, p0, p1 = at(fy["sales"], j), at(fy["sales_1"], j), at(fy["np"], j), at(fy["np_1"], j)
        if k in ("A1", "B1", "A2", "A6"):
            base = f"sales {_f(ch(s0, s1), '{:+.0f}')}%, profit {_f(ch(p0, p1), '{:+.0f}')}% in the latest year"
            if k == "B1":
                m = at(mc, j)
                return base + f"; P/E {_f(m / p0 if m and p0 else None, '{:.0f}')}"
            if k == "A2":
                o0, o1 = at(fy["op"], j), at(fy["op_1"], j)
                return base + f"; operating margin {_f(o1 / s1 * 100 if o1 and s1 else None, '{:.0f}')}% → {_f(o0 / s0 * 100 if o0 and s0 else None, '{:.0f}')}%"
            if k == "A6":
                return base + f", after investing ₹{_f(-(at(fy['cfi_1'], j) or 0))} Cr the year before"
            return base
        if k == "A3":
            return f"profit ₹{_f(p0)} Cr after a loss of ₹{_f(-(p1 or 0))} Cr; sales {_f(ch(s0, s1), '{:+.0f}')}%"
        if k == "A4":
            return f"ROCE {_f(at(fy['roce_1'], j), '{:.0f}')}% → {_f(at(fy['roce'], j), '{:.0f}')}%"
        if k == "A5":
            return f"borrowings ₹{_f(at(fy['borrow_1'], j))} → ₹{_f(at(fy['borrow'], j))} Cr while sales grew"
        if k == "B2":
            m = at(mc, j)
            fcf = (at(fy["cfo"], j) or 0) + (at(fy["cfi"], j) or 0)
            return f"free-cash-flow yield {_f(fcf / m * 100 if m else None, '{:.1f}')}%, book/market {_f((at(fy['eq'], j) or 0) / m if m else None, '{:.2f}')}"
        if k == "B3":
            return f"market cap ₹{_f(at(mc, j))} Cr"
        if k in ("C1", "C2", "C3"):
            a0 = (at(sh["fii"], j) or 0) + (at(sh["dii"], j) or 0)
            a1 = (at(sh["fii_1"], j) or 0) + (at(sh["dii_1"], j) or 0)
            return f"FII + DII {a1:.1f}% → {a0:.1f}% (March to March)" if k != "C2" else f"FII + DII only {a0:.1f}%"
        if k == "C4":
            return f"shareholders {_f(at(sh['nsh_1'], j))} → {_f(at(sh['nsh'], j))}"
        if k in ("D1", "D2"):
            return f"promoter holding {_f(at(sh['prom_1'], j), '{:.1f}')}% → {_f(at(sh['prom'], j), '{:.1f}')}%"
        if k == "E1":
            return "delivery share well above its own yearly average, with the price rising"
        if k == "E2":
            return "more volume on up days than down days over 50 sessions"
        if k == "E3":
            tv = g.tv[:, j]
            a20, a120 = np.nanmean(tv[max(0, t - 19):t + 1]), np.nanmean(tv[max(0, t - 119):t + 1])
            return f"traded value {a20 / a120:.1f}× its 6-month average" if a120 else "traded value surging"
        if k == "F ":
            return "a price leader: RS leader or trend template"
        if k == "Q1":
            q = T["quarterly"]
            rows = q[q["symbol"] == sym].sort_values("qend") if len(q) else q
            if len(rows) >= 5:
                r, prev = rows.iloc[-1], rows[rows["qend"] <= str((pd.Timestamp(rows.iloc[-1]["qend"]) - pd.DateOffset(years=1) + pd.offsets.MonthEnd(0)).date())]
                if len(prev):
                    pv = prev.iloc[-1]
                    return f"{pd.Timestamp(r['qend']):%b %Y} quarter: profit {_f(ch(r['pat'], pv['pat']), '{:+.0f}')}%, sales {_f(ch(r['rev'], pv['rev']), '{:+.0f}')}% on a year before"
            return "the latest quarter's profit and sales well up on a year before"
        if name == mb_score.H25_KEY:
            from research.insider_study import promoter_purchases
            rows = promoter_purchases(tr[tr["symbol"] == sym]) if len(tr) else tr   # the purchases H25 counts
            if len(rows):
                r = rows.sort_values("disclosed_at").iloc[-1]
                return f"a promoter bought ₹{(r['value'] or 0) / 1e5:,.1f} lakh (disclosed {str(r['disclosed_at'])[:10]}), and the stock is a price leader"
            return "a promoter bought in the market in the last 60 sessions, and the stock is a price leader"
        return ""
    return evid
