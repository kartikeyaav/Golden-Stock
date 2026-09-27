"""
research/insider_study.py — H21-H29 of PREREG_2026-09-27_promoter_buying.md,
scored exactly like the multibagger event study (research/event_study.py).

    python -m research.insider_study
"""

from __future__ import annotations

import json
import os
import time

import numpy as np
import pandas as pd

from data.insider import RESEARCH_PATH
from data.nse_history import _symbol_chain
from research.event_study import HORIZONS, LABELS, dedupe, mechanical_exit, summarise
from research.grid import fwd_max, load_grid, roll
from research.hypotheses import h4_trend_template, h9_rs_leader

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
DISCOVERY_END = pd.Timestamp("2020-12-31")
CLOSE_TIME = pd.Timedelta(hours=15, minutes=30)
PROMOTER = ("promoter", "promoter_group")


def load_trades() -> pd.DataFrame:
    df = pd.read_csv(RESEARCH_PATH, parse_dates=["disclosed_at", "trade_from", "trade_to"])
    df = df[df["disclosed_at"].notna() & df["symbol"].notna()]
    chain = _symbol_chain()
    df["symbol"] = df["symbol"].astype(str).str.strip().map(lambda s: chain.get(s, s))
    df["mode_l"] = df["mode"].fillna("").str.lower()
    return df


def signal_rows(g, trades: pd.DataFrame) -> pd.DataFrame:
    """Each disclosure -> (session index, column). The signal session is the
    first session whose close (15:30 IST) falls AFTER the disclosure.

    A reused ticker is split into incarnations (NAME, NAME~2, ... — oldest
    first; data/nse_history). A disclosure belongs to the incarnation TRADING
    at its session. Matching by name alone sent it to the oldest company:
    2026-09-28, 43 promoter purchases on 4 tickers (PREMIERPOL, PVP, KMSUGAR,
    ADROITINFO) had landed on a company that no longer traded."""
    closes = g.dates + CLOSE_TIME
    t = np.searchsorted(closes.values, trades["disclosed_at"].values, side="right")
    col = {s: j for j, s in enumerate(g.symbols)}
    out = trades.assign(t=t, j=trades["symbol"].map(col))
    reused: dict[str, list[int]] = {}
    for k, s in enumerate(g.symbols):
        reused.setdefault(s.split("~")[0], []).append(k)
    reused = {b: ks for b, ks in reused.items() if len(ks) > 1}
    m = out["symbol"].isin(reused)
    if m.any():
        fin = np.isfinite(g.c)
        span = {}                                    # column -> first and last session with a close
        for ks in reused.values():
            for k in ks:
                idx = np.flatnonzero(fin[:, k])
                span[k] = (idx[0], idx[-1]) if len(idx) else (g.T, -1)

        def trading_at(sym: str, tt: int) -> int:
            ks, tt = reused[sym], min(tt, g.T - 1)
            inside = [k for k in ks if span[k][0] <= tt <= span[k][1]]
            if inside:
                return inside[0]
            began = [k for k in ks if span[k][0] <= tt]  # between lives: the last one that began
            return max(began, key=lambda k: span[k][0]) if began else ks[0]

        out.loc[m, "j"] = [trading_at(s, tt) for s, tt in zip(out.loc[m, "symbol"], out.loc[m, "t"])]
    return out[out["j"].notna() & (out["t"] < g.T)].astype({"j": int})


def grid_of(g, rows: pd.DataFrame) -> np.ndarray:
    m = np.zeros((g.T, g.N), dtype=bool)
    m[rows["t"].to_numpy(), rows["j"].to_numpy()] = True
    return m


def promoter_purchases(tr: pd.DataFrame, min_value: float = 10e5) -> pd.DataFrame:
    """H21's rows: promoter / promoter-group MARKET purchases worth >= min_value."""
    mode = tr["mode"].fillna("").str.lower() if "mode_l" not in tr else tr["mode_l"]
    return tr[tr["category"].isin(PROMOTER) & (tr["txn"] == "buy")
              & mode.str.contains("market purchase") & (tr["value"].fillna(0) >= min_value)]


def h25_grid(g, tr: pd.DataFrame, window: int = 60) -> np.ndarray:
    """H25 (the survivor of PREREG_2026-09-27_promoter_buying.md): an H21
    purchase disclosed in the prior `window` sessions AND the stock is an RS
    leader or passes the trend template today. The radar calls this."""
    h21 = grid_of(g, signal_rows(g, promoter_purchases(tr)))
    recent = roll(h21.astype("float32"), window, "max", minp=1) > 0
    return recent & (h9_rs_leader(g) | h4_trend_template(g))


def hypotheses(g, tr: pd.DataFrame) -> dict[str, np.ndarray]:
    buy = (tr["txn"] == "buy") & tr["mode_l"].str.contains("market purchase")
    sell = (tr["txn"] == "sell") & tr["mode_l"].str.contains("market sale")
    prom = tr["category"].isin(PROMOTER)
    v = tr["value"].fillna(0)
    h21 = tr[prom & buy & (v >= 10e5)]
    h22 = tr[prom & buy & (v >= 1e7)]
    # H23: a cluster — >= 2 promoter market-purchase disclosures within 30 days, >= Rs 25 lakh together
    pb = tr[prom & buy].sort_values("disclosed_at")
    rows = []
    for sym, grp in pb.groupby("symbol"):
        ts = grp["disclosed_at"].to_numpy()
        vals = grp["value"].fillna(0).to_numpy()
        for k in range(len(grp)):
            lo = np.searchsorted(ts, ts[k] - np.timedelta64(30, "D"), side="left")
            if k - lo + 1 >= 2 and vals[lo:k + 1].sum() >= 25e5:
                rows.append(grp.iloc[k])
    h23 = pd.DataFrame(rows) if rows else pb.iloc[0:0]
    up = (tr["pct_after"] - tr["pct_before"])
    h24 = tr[prom & buy & (up >= 0.10)]
    h26 = tr[tr["category"].isin(("director", "kmp")) & buy & (v >= 10e5)]
    h27 = tr[prom & sell & (v >= 1e7)]
    h28 = tr[prom & (tr["txn"] == "pledge")]
    h29 = tr[prom & (tr["txn"] == "pledge_revoke")]
    out = {}
    for name, sub in (("H21 promoter market purchase >= Rs 10 lakh", h21),
                      ("H22 promoter market purchase >= Rs 1 crore", h22),
                      ("H23 promoter purchase cluster (2+ in 30 days)", h23),
                      ("H24 promoter stake increase >= 0.10 pp", h24),
                      ("H26 director/KMP market purchase >= Rs 10 lakh", h26),
                      ("H27 promoter market sale >= Rs 1 crore (negative control)", h27),
                      ("H28 promoter pledge creation (negative control)", h28),
                      ("H29 promoter pledge revocation", h29)):
        out[name] = grid_of(g, signal_rows(g, sub))
    # H25: an H21 purchase in the prior 60 sessions AND an RS leader or trend-template pass today
    recent = roll(out["H21 promoter market purchase >= Rs 10 lakh"].astype("float32"), 60, "max", minp=1) > 0
    out["H25 promoter purchase (60d) + RS leader or trend template"] = recent & (h9_rs_leader(g) | h4_trend_template(g))
    return out


def main() -> int:
    t0 = time.time()
    g = load_grid()
    U = g.universe()
    tr = load_trades()
    print(f"{len(tr):,} disclosures {tr['disclosed_at'].min():%Y-%m-%d} -> {tr['disclosed_at'].max():%Y-%m-%d}; "
          f"promoter market purchases {int(((tr['category'].isin(PROMOTER)) & (tr['txn'] == 'buy') & tr['mode_l'].str.contains('market purchase')).sum()):,}",
          flush=True)
    lab = {k: g.mb(m, w) for k, (m, w) in LABELS.items()}
    base = {k: np.nanmean(np.where(U, v, np.nan), axis=1) for k, v in lab.items()}
    fr = {h: g.fwd_ret(h) for h in HORIZONS}
    fr_base = {h: np.nanmean(np.where(U, v, np.nan), axis=1) for h, v in fr.items()}
    lo250 = roll(g.c, 250, "min", minp=60)
    pk = fwd_max(g.c, 252)
    # the calibration sample, restricted to the insider-data era
    era = (g.dates >= pd.Timestamp("2015-06-01"))[:, None]
    rng = np.random.default_rng(7)
    tests = {"H0 every universe stock (2015-06 on)": U & era & (rng.random(U.shape) < 1 / 60),
             **hypotheses(g, tr)}
    results = {}
    for name, sig in tests.items():
        t, j = dedupe(sig & U)
        ev = pd.DataFrame({"t": t, "j": j})
        ev["date"] = g.dates[t]
        for k, v in lab.items():
            ev[k] = v[t, j]
            ev[f"base_{k}"] = base[k][t]
        for h in HORIZONS:
            ev[f"r{h}"] = fr[h][t, j]
            ev[f"x{h}"] = fr[h][t, j] - fr_base[h][t]
        e = g.entry()[t, j]
        with np.errstate(divide="ignore", invalid="ignore"):
            ev["early"] = np.log(pk[t, j] / e) / np.log(pk[t, j] / lo250[t, j])
        ev["mult"], ev["held"] = mechanical_exit(g, t, j)
        disc, conf = ev[ev["date"] <= DISCOVERY_END], ev[ev["date"] > DISCOVERY_END]
        results[name] = {"all": summarise(ev), "discovery": summarise(disc), "confirmation": summarise(conf)}
        d = results[name]["discovery"].get("MB3_1y", {})
        c = results[name]["confirmation"].get("MB3_1y", {})
        print(f"{name:60} n={len(ev):5} (disc {len(disc)}, conf {len(conf)})  MB3_1y lift disc {d.get('lift')} "
              f"conf {c.get('lift')}", flush=True)
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(os.path.join(OUT_DIR, "insider_study.json"), "w", encoding="utf-8") as f:
        json.dump({"discovery_end": str(DISCOVERY_END.date()), "results": results}, f, indent=1, default=str)
    print(f"done in {(time.time() - t0) / 60:.1f}m")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
