"""
research/factor_study.py — PREREG_2026-09-29_multibagger_factors.md.

Which fundamental, institutional, management and volume parameters preceded
Indian multibaggers, alone and combined? Every factor is point in time:
  annual statements   fiscal year Y known from 1 October Y
  shareholding        the March Y snapshot known from 1 May Y
  market cap          the fetch-date market cap scaled by the adjusted price
  volume, delivery    the session itself (NSE bhavcopy and MTO files)
Scored exactly like the earlier event studies: each stock's first firing
per 120 sessions, the lift of tripling within a year against the same-date
universe, 2016-2020 (discovery) then 2021-2026 (confirmation).

    python -m research.factor_study
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

import numpy as np
import pandas as pd

from research import fundamentals as F
from research.event_study import HORIZONS, LABELS, dedupe, mechanical_exit, summarise
from research.grid import fwd_max, load_grid, roll, shift, xrank
from research.hypotheses import h4_trend_template, h9_rs_leader
from research.insider_study import grid_of, load_trades, promoter_purchases, signal_rows
from research.shareholding_fetch import OUT as SHP_DIR

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
START, SPLIT = pd.Timestamp("2016-01-01"), pd.Timestamp("2020-12-31")


# ------------------------------------------------------------------ data
def annual_table() -> pd.DataFrame:
    """Every fiscal year of every company in the screener.in research cache."""
    rows = []
    for p in sorted(Path(F.FUND_DIR).glob("*.json")):
        if p.name.startswith("_"):
            continue
        d = json.loads(p.read_text(encoding="utf-8"))
        pl, bs, cf, ra = d.get("profit_loss"), d.get("balance_sheet"), d.get("cash_flow"), d.get("ratios")

        def ser(tbl, *labels):
            for lab in labels:
                s = F._series(tbl, lab)
                if s:
                    return s
            return {}
        sales, op, npf = ser(pl, "Sales", "Revenue"), ser(pl, "Operating Profit", "Financing Profit"), ser(pl, "Net Profit")
        cfo, cfi = ser(cf, "Cash from Operating Activity"), ser(cf, "Cash from Investing Activity")
        ec, rs, bor, ta = ser(bs, "Equity Capital"), ser(bs, "Reserves"), ser(bs, "Borrowings"), ser(bs, "Total Assets")
        roce = ser(ra, "ROCE %")
        tr = d.get("top_ratios") or {}
        for y in sorted(set(sales) | set(npf) | set(ec)):
            eq = ec.get(y) + rs.get(y) if ec.get(y) is not None and rs.get(y) is not None else None
            rows.append({"symbol": p.stem, "fy": y, "sales": sales.get(y), "op": op.get(y), "np": npf.get(y),
                         "cfo": cfo.get(y), "cfi": cfi.get(y), "eq": eq, "borrow": bor.get(y), "assets": ta.get(y),
                         "roce": roce.get(y), "mcap_now": tr.get("Market Cap"), "price_now": tr.get("Current Price"),
                         "fetched_at": d.get("fetched_at")})
    return pd.DataFrame(rows)


def shp_table() -> pd.DataFrame:
    """Every March shareholding snapshot in the screener_shp cache."""
    rows = []
    for p in sorted(Path(SHP_DIR).glob("*.json")):
        if p.name.startswith("_"):
            continue
        y = ((json.loads(p.read_text(encoding="utf-8")).get("shareholding") or {}).get("yearly") or {})
        cols, R = y.get("columns") or [], y.get("rows") or {}

        def at(k, i):
            v = R.get(k) or []
            return v[i] if i < len(v) else None
        for i, c in enumerate(cols):
            if str(c).startswith("Mar "):
                rows.append({"symbol": p.stem, "yr": int(str(c)[4:]), "prom": at("Promoters", i), "fii": at("FIIs", i),
                             "dii": at("DIIs", i), "nsh": at("No. of Shareholders", i)})
    return pd.DataFrame(rows)


def _latest_col(g) -> dict[str, int]:
    col: dict[str, int] = {}
    for j, s in enumerate(g.symbols):
        col[s.split("~")[0]] = j                       # today's company for a reused ticker
    return col


def dated_grids(g, tab: pd.DataFrame, key: str, fields, known_md: str, backs=(0, 1)) -> dict[str, np.ndarray]:
    """For each field: the value of the latest period KNOWN at each session
    (period Y from `Y-known_md`), and of the periods before it (`f_1`, ...)."""
    T, N = g.T, g.N
    sfx = {0: "", 1: "_1", 2: "_2"}
    out = {f"{f}{sfx[b]}": np.full((T, N), np.nan, "float32") for f in fields for b in backs}
    known = {y: int(np.searchsorted(g.dates.values, np.datetime64(f"{y}-{known_md}"))) for y in range(2005, 2032)}
    col = _latest_col(g)
    for sym, grp in tab.groupby("symbol"):
        j = col.get(str(sym))
        if j is None:
            continue
        by = {int(getattr(r, key)): r for r in grp.itertuples()}
        years = sorted(by)
        for k, y in enumerate(years):
            a = known.get(y)
            if a is None or a >= T:
                continue
            b = min(known.get(years[k + 1], T) if k + 1 < len(years) else T, T)
            for f in fields:
                for back in backs:
                    r = by.get(y - back)
                    v = getattr(r, f) if r is not None else None
                    out[f"{f}{sfx[back]}"][a:b, j] = v if v is not None and pd.notna(v) else np.nan
    return out


def mcap_grid(g, tab: pd.DataFrame) -> np.ndarray:
    """Market cap (Rs crore) at every session: the fetch-date market cap
    scaled by the adjusted price."""
    T, N = g.T, g.N
    mc = np.full((T, N), np.nan, "float32")
    col = _latest_col(g)
    cf = pd.DataFrame(g.c).ffill().to_numpy()
    first = tab.drop_duplicates("symbol")
    for r in first.itertuples():
        j = col.get(str(r.symbol))
        if j is None or r.mcap_now is None or pd.isna(r.mcap_now) or not r.fetched_at:
            continue
        t_f = int(np.searchsorted(g.dates.values, np.datetime64(str(r.fetched_at)[:10]), side="right")) - 1
        t_f = min(max(t_f, 0), T - 1)
        c_f = cf[t_f, j]
        if np.isfinite(c_f) and c_f > 0:
            mc[:, j] = float(r.mcap_now) * g.c[:, j] / c_f
    return mc



RES_DIR = Path(SHP_DIR).parent / "results"
_MON = {m: i for i, m in enumerate(("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"), 1)}


def quarterly_table() -> pd.DataFrame:
    """Quarterly revenue and profit (Rs crore): NSE's filed results (XBRL,
    2017-2024; known from the exchange broadcast) and screener.in's last 13
    quarters (known 45 days after quarter end, SEBI's deadline). Where both
    have a quarter, NSE's exact filing time wins."""
    rows = []
    for fp in sorted(RES_DIR.glob("*.json")) if RES_DIR.exists() else []:
        if fp.name.startswith("_"):
            continue
        for q in json.loads(fp.read_text(encoding="utf-8")).get("quarters") or []:
            if q.get("revenue") is None or q.get("profit") is None:
                continue
            rows.append({"symbol": fp.stem, "qend": q["end"][:10], "known": q["filed"][:10],
                         "rev": q["revenue"] / 1e7, "pat": q["profit"] / 1e7, "src": 0})
    for fp in sorted(Path(F.FUND_DIR).glob("*.json")):
        if fp.name.startswith("_"):
            continue
        qt = json.loads(fp.read_text(encoding="utf-8")).get("quarters") or {}
        cols, R = qt.get("columns") or [], qt.get("rows") or {}
        rev, pat = R.get("Sales") or R.get("Revenue") or [], R.get("Net Profit") or []
        for i, c in enumerate(cols):
            parts = str(c).split()
            if len(parts) != 2 or parts[0] not in _MON or i >= len(rev) or i >= len(pat) or rev[i] is None or pat[i] is None:
                continue
            end = (pd.Timestamp(int(parts[1]), _MON[parts[0]], 1) + pd.offsets.MonthEnd(0))
            rows.append({"symbol": fp.stem, "qend": str(end.date()), "known": str((end + pd.Timedelta(days=45)).date()),
                         "rev": rev[i], "pat": pat[i], "src": 1})
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    return df.sort_values("src").drop_duplicates(["symbol", "qend"], keep="first").sort_values(["symbol", "qend"])


def q_grid(g, qt: pd.DataFrame) -> np.ndarray:
    """Q1 (PREREG amendment 2026-09-29): the latest KNOWN quarter's profit up
    >= 25% on the same quarter a year before (which was a profit) and its
    sales up >= 20%; on from the day it became known until the next quarter's."""
    T, N = g.T, g.N
    out = np.zeros((T, N), bool)
    col = _latest_col(g)
    for sym, grp in qt.groupby("symbol"):
        j = col.get(str(sym))
        if j is None:
            continue
        grp = grp.sort_values("qend")
        by = {r.qend: r for r in grp.itertuples()}
        ends = list(by)
        for k, e in enumerate(ends):
            r = by[e]
            prev = by.get(str((pd.Timestamp(e) - pd.DateOffset(years=1) + pd.offsets.MonthEnd(0)).date()))
            a = int(np.searchsorted(g.dates.values, np.datetime64(r.known), side="right"))
            b = int(np.searchsorted(g.dates.values, np.datetime64(by[ends[k + 1]].known), side="right")) if k + 1 < len(ends) else T
            if prev is None or a >= T or b <= a:
                continue
            if prev.pat > 0 and r.pat >= 1.25 * prev.pat and prev.rev > 0 and r.rev >= 1.20 * prev.rev:
                out[a:b, j] = True
    return out


# --------------------------------------------------------------- factors
def factors(g, fy: dict, sh: dict, mc: np.ndarray, promo60: np.ndarray) -> dict[str, np.ndarray]:
    U = g.universe()
    with np.errstate(divide="ignore", invalid="ignore"):
        sg = fy["sales"] / fy["sales_1"] - 1
        pg = fy["np"] / fy["np_1"] - 1
        opm, opm1 = fy["op"] / fy["sales"], fy["op_1"] / fy["sales_1"]
        A = {
            "A1 growth: sales and profit up 20%+": (sg >= 0.20) & (fy["np_1"] > 0) & (pg >= 0.20) & (fy["np"] > 0),
            "A2 operating leverage: margin +3 pts, profit outgrowing sales": ((opm - opm1) >= 0.03) & (fy["np_1"] > 0) & (pg > sg) & (sg > 0.10),
            "A3 turnaround: profit after a loss year, sales up": (fy["np_1"] < 0) & (fy["np"] > 0) & (fy["sales"] > fy["sales_1"]),
            "A4 returns rising: ROCE +5 pts to 15%+": ((fy["roce"] - fy["roce_1"]) >= 5) & (fy["roce"] >= 15),
            "A5 deleveraging: debt -25%, sales up": (fy["borrow_1"] >= 0.10 * fy["eq_1"]) & (fy["borrow"] <= 0.75 * fy["borrow_1"]) & (fy["sales"] > fy["sales_1"]),
            "A6 capacity coming on stream: big capex, then sales +20%": ((-fy["cfi_1"]) >= 0.15 * fy["assets_1"]) & (sg >= 0.20),
        }
        pe = mc / fy["np"]
        fcfy, bm = (fy["cfo"] + fy["cfi"]) / mc, fy["eq"] / mc
        B = {
            "B1 cheap for its growth: P/E 20 or less, profit +20%": (fy["np"] > 0) & (pe > 0) & (pe <= 20) & (fy["np_1"] > 0) & (pg >= 0.20),
            "B2 value: FCF yield and book/market top 30%": (xrank(fcfy, U & np.isfinite(fcfy)) >= 0.7) & (xrank(bm, U & np.isfinite(bm)) >= 0.7) & (fcfy > 0),
            "B3 small: market cap under Rs 2,000 Cr": (mc > 0) & (mc <= 2000),
        }
        inst, inst1 = sh["fii"] + sh["dii"], sh["fii_1"] + sh["dii_1"]
        C = {
            "C1 institutions arriving: FII+DII +2 pts from under 10%": ((inst - inst1) >= 2) & (inst1 < 10),
            "C2 undiscovered: FII+DII under 5%": inst < 5,
            "C3 institutions adding: FII+DII +3 pts": (inst - inst1) >= 3,
            "C4 shareholder base +25%": (sh["nsh"] >= 1.25 * sh["nsh_1"]) & (sh["nsh_1"] > 0),
        }
        Dm = {
            "D1 promoter raising stake: +1 pt": (sh["prom"] - sh["prom_1"]) >= 1,
            "D2 promoter holding 50%+": sh["prom"] >= 50,
            "D3 promoter cutting stake: -3 pts (negative control)": (sh["prom_1"] - sh["prom"]) >= 3,
        }
        dshare = np.where(g.v > 0, g.dq / g.v, np.nan).astype("float32")
        d20, d250 = roll(dshare, 20, "mean", minp=15), roll(dshare, 250, "mean", minp=150)
        s50 = g.sma(50)
        up = g.c > shift(g.c, 1)
        dn = g.c < shift(g.c, 1)
        uv = roll(np.where(up, g.v, 0.0).astype("float32"), 50, "sum", minp=40)
        dv = roll(np.where(dn, g.v, 0.0).astype("float32"), 50, "sum", minp=40)
        tv20, tv120 = roll(g.tv, 20, "mean", minp=15), roll(g.tv, 120, "mean", minp=80)
        E = {
            "E1 delivery accumulation": (d20 >= 1.25 * d250) & (g.c > s50) & (g.ret(20) > 0),
            "E2 up/down volume 1.5x": (uv >= 1.5 * dv) & (dv > 0) & (g.c > s50),
            "E3 volume expansion: traded value 2x": tv20 >= 2 * tv120,
        }
    mom = h9_rs_leader(g) | h4_trend_template(g)
    b = lambda x: np.nan_to_num(x).astype(bool)      # NaN = unknown = no signal
    A, B, C, Dm, E = ({k: b(v) for k, v in grp.items()} for grp in (A, B, C, Dm, E))
    a_any = np.logical_or.reduce(list(A.values()))
    fam = (a_any.astype(int) + (B["B1 cheap for its growth: P/E 20 or less, profit +20%"] | B["B2 value: FCF yield and book/market top 30%"]).astype(int)
           + (C["C1 institutions arriving: FII+DII +2 pts from under 10%"] | C["C3 institutions adding: FII+DII +3 pts"] | C["C4 shareholder base +25%"]).astype(int)
           + (Dm["D1 promoter raising stake: +1 pt"] | promo60).astype(int)
           + (E["E1 delivery accumulation"] | E["E2 up/down volume 1.5x"]).astype(int) + mom.astype(int))
    A1, A2, A3, A4 = (A[k] for k in list(A)[:4])
    K = {
        "K1 twin engines: growth + cheap for its growth": A1 & B["B1 cheap for its growth: P/E 20 or less, profit +20%"],
        "K2 institutions arriving + momentum": C["C1 institutions arriving: FII+DII +2 pts from under 10%"] & mom,
        "K3 inflection + institutions": (A1 | A2 | A3) & (C["C1 institutions arriving: FII+DII +2 pts from under 10%"] | C["C3 institutions adding: FII+DII +3 pts"]),
        "K4 full stack: inflection + ownership + volume + momentum": (A1 | A2 | A3 | A4) & (C["C1 institutions arriving: FII+DII +2 pts from under 10%"] | C["C3 institutions adding: FII+DII +3 pts"] | Dm["D1 promoter raising stake: +1 pt"]) & (E["E1 delivery accumulation"] | E["E2 up/down volume 1.5x"]) & mom,
        "K5 family count 3+": fam >= 3,
        "K5 family count 4+": fam >= 4,
        "K5 family count 5+": fam >= 5,
    }
    return {**A, **B, **C, **Dm, **E, "F momentum alone (RS leader or trend template)": mom, **K}


# ------------------------------------------------------------------ main
def main() -> int:
    t0 = time.time()
    g = load_grid()
    U = g.universe()
    at, st = annual_table(), shp_table()
    fy = dated_grids(g, at, "fy", ("sales", "op", "np", "cfo", "cfi", "eq", "borrow", "assets", "roce"), "10-01", backs=(0, 1))
    sh = dated_grids(g, st, "yr", ("prom", "fii", "dii", "nsh"), "05-01", backs=(0, 1))
    mc = mcap_grid(g, at)
    tr = load_trades()
    promo60 = roll(grid_of(g, signal_rows(g, promoter_purchases(tr))).astype("float32"), 60, "max", minp=1) > 0
    era = (g.dates >= START)[:, None]
    have_f = np.isfinite(fy["np"]) & np.isfinite(fy["np_1"])
    have_s = np.isfinite(sh["fii"]) & np.isfinite(sh["fii_1"])
    cells = (U & era).sum()
    cover = {"fundamentals_pct": round(float((U & era & have_f).sum() / cells * 100), 1),
             "shareholding_pct": round(float((U & era & have_s).sum() / cells * 100), 1),
             "companies_annual": int(at["symbol"].nunique()), "companies_shareholding": int(st["symbol"].nunique()) if len(st) else 0}
    print(f"grids ready ({time.time() - t0:.0f}s); coverage of universe cells since 2016: {cover}", flush=True)
    rng = np.random.default_rng(7)
    qt = quarterly_table()
    q1 = q_grid(g, qt) if len(qt) else np.zeros_like(U)
    have_q = int(qt["symbol"].nunique()) if len(qt) else 0
    print(f"quarterly results: {have_q} companies, {len(qt):,} company-quarters", flush=True)
    tests = {"H0 random universe stock with fundamentals": U & era & have_f & (rng.random(U.shape) < 1 / 60),
             **{k: v & era for k, v in factors(g, fy, sh, mc, promo60).items()},
             "Q1 quarterly: profit +25%, sales +20% on the same quarter last year": q1 & era}
    # the 1 June timing sensitivity (PREREG amendment 2026-09-29): the same
    # annual-statement factors, with fiscal year Y known from 1 June Y
    fy_jun = dated_grids(g, at, "fy", ("sales", "op", "np", "cfo", "cfi", "eq", "borrow", "assets", "roce"), "06-01", backs=(0, 1))
    annual_keys = [k for k in tests if k[:2] in ("A1", "A2", "A3", "A4", "A5", "A6", "B1", "B2", "K1", "K3", "K4", "K5")]
    sens = {k: v & era for k, v in factors(g, fy_jun, sh, mc, promo60).items() if k in annual_keys}
    lab = {k: g.mb(m, w) for k, (m, w) in LABELS.items()}
    base = {k: np.nanmean(np.where(U, v, np.nan), axis=1) for k, v in lab.items()}
    fr = {h: g.fwd_ret(h) for h in HORIZONS}
    fr_base = {h: np.nanmean(np.where(U, v, np.nan), axis=1) for h, v in fr.items()}
    lo250, pk = roll(g.c, 250, "min", minp=60), fwd_max(g.c, 252)
    res, res_jun = {}, {}
    for block, name, sig in [("reg", k, v) for k, v in tests.items()] + [("jun", k, v) for k, v in sens.items()]:
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
        disc, conf = ev[ev["date"] <= SPLIT], ev[ev["date"] > SPLIT]
        out = res if block == "reg" else res_jun
        out[name] = {"all": summarise(ev), "discovery": summarise(disc), "confirmation": summarise(conf)}
        d, c = out[name]["discovery"].get("MB3_1y", {}), out[name]["confirmation"].get("MB3_1y", {})
        m12 = out[name]["confirmation"].get("r252", {}).get("median")
        tag = "" if block == "reg" else "[1 June] "
        print(f"{tag}{name:66} n {len(disc):5}/{len(conf):5}  lift {d.get('lift')} / {c.get('lift')}  12m median (21-26) {m12}", flush=True)
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(os.path.join(OUT_DIR, "factor_study.json"), "w", encoding="utf-8") as f:
        json.dump({"split": str(SPLIT.date()), "coverage": {**cover, "companies_quarterly": have_q},
                   "results": res, "sensitivity_1_june": res_jun}, f, indent=1, default=str)
    print(f"done in {(time.time() - t0) / 60:.1f}m")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
