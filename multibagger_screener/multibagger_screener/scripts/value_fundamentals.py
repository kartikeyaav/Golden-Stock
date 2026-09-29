"""
scripts/value_fundamentals.py — the annual fundamentals the cheap + new uptrend
signal needs, for the WHOLE liquid market, kept in one committed file.

WHY. The radar computes H20 (PREREG_2026-09-26 H20; forward test
PREREG_2026-09-27_value_breakout.md) nightly on every liquid NSE stock, and H20
needs each company's free cash flow and book value by fiscal year. The live
fundamentals_cache holds only the shortlist and lacks the investing cash flow,
so this keeps a compact table instead:

    value_fundamentals.csv   symbol, fy, cfo, cfi, eq, sales, np, mcap_now,
                             price_now, fetched_at     (one row per company-year)

It is refreshed by the weekly cloud job, the ~400 stalest companies per run
(a full cycle about monthly — annual accounts change once a year), using the
research fetcher and parser (research/fundamentals_fetch.py), so the live
numbers come from the same extraction the study measured.

    python scripts/value_fundamentals.py                  # weekly refresh (cloud)
    python scripts/value_fundamentals.py --seed-from-cache  # build from the research cache
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

CSV = os.path.join(ROOT, "value_fundamentals.csv")
# the same pages carry shareholding and the last 13 quarters: kept too, for the
# multibagger factors (PREREG_2026-09-29) and the stock view (2026-09-29)
SHP_CSV = os.path.join(ROOT, "shareholding.csv")
QTR_CSV = os.path.join(ROOT, "quarterly_results.csv")
SHP_COLS = ["symbol", "kind", "period", "prom", "fii", "dii", "nsh", "fetched_at"]
QTR_COLS = ["symbol", "qend", "sales", "op", "np", "eps", "fetched_at"]
_MON = {m: i for i, m in enumerate(("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"), 1)}
RADAR_STATE = os.path.join(ROOT, "state", "multibagger_radar.json")
COLS = ["symbol", "fy", "cfo", "cfi", "eq", "sales", "np", "mcap_now", "price_now", "fetched_at"]
STALE_DAYS = 28
PER_RUN = 400


def rows_from_page(sym: str, d: dict) -> list[dict]:
    from research.fundamentals import _series
    pl, bs, cf = d.get("profit_loss"), d.get("balance_sheet"), d.get("cash_flow")
    sales = _series(pl, "Sales") or _series(pl, "Revenue")
    npf = _series(pl, "Net Profit")
    cfo = _series(cf, "Cash from Operating Activity")
    cfi = _series(cf, "Cash from Investing Activity")
    ec, rs = _series(bs, "Equity Capital"), _series(bs, "Reserves")
    tr = d.get("top_ratios") or {}
    fetched = str(d.get("fetched_at") or datetime.now().isoformat(timespec="seconds"))[:10]
    out = []
    for y in sorted(set(sales) | set(ec) | set(cfo)):
        eq = (ec.get(y) + rs.get(y)) if (y in ec and y in rs) else None
        out.append({"symbol": sym, "fy": y, "cfo": cfo.get(y), "cfi": cfi.get(y), "eq": eq,
                    "sales": sales.get(y), "np": npf.get(y), "mcap_now": tr.get("Market Cap"),
                    "price_now": tr.get("Current Price"), "fetched_at": fetched})
    return out


def _period(col: str) -> str | None:
    parts = str(col).split()
    if len(parts) != 2 or parts[0] not in _MON or not parts[1].isdigit():
        return None
    return f"{parts[1]}-{_MON[parts[0]]:02d}"


def shp_rows_from_page(sym: str, d: dict) -> list[dict]:
    fetched = str(d.get("fetched_at") or datetime.now().isoformat(timespec="seconds"))[:10]
    out = []
    for kind in ("yearly", "quarterly"):
        tbl = (d.get("shareholding") or {}).get(kind) or {}
        cols, R = tbl.get("columns") or [], tbl.get("rows") or {}
        for i, c in enumerate(cols):
            per = _period(c)
            if not per:
                continue
            at = lambda k: (R.get(k) or [None] * (i + 1))[i] if i < len(R.get(k) or []) else None
            out.append({"symbol": sym, "kind": kind, "period": per, "prom": at("Promoters"), "fii": at("FIIs"),
                        "dii": at("DIIs"), "nsh": at("No. of Shareholders"), "fetched_at": fetched})
    return out


def q_rows_from_page(sym: str, d: dict) -> list[dict]:
    fetched = str(d.get("fetched_at") or datetime.now().isoformat(timespec="seconds"))[:10]
    tbl = d.get("quarters") or {}
    cols, R = tbl.get("columns") or [], tbl.get("rows") or {}
    sales = R.get("Sales") or R.get("Revenue") or []
    out = []
    for i, c in enumerate(cols):
        per = _period(c)
        if not per:
            continue
        end = (pd.Timestamp(per + "-01") + pd.offsets.MonthEnd(0)).date()
        at = lambda v: v[i] if i < len(v) else None
        out.append({"symbol": sym, "qend": str(end), "sales": at(sales), "op": at(R.get("Operating Profit") or []),
                    "np": at(R.get("Net Profit") or []), "eps": at(R.get("EPS in Rs") or []), "fetched_at": fetched})
    return out


def _save_table(rows_by_sym: dict, path: str, cols: list[str], keys: list[str]) -> None:
    """Replace each fetched symbol's rows in a committed table."""
    try:
        old = pd.read_csv(path)
    except (OSError, ValueError):
        old = pd.DataFrame(columns=cols)
    fresh = pd.DataFrame([r for rows in rows_by_sym.values() for r in rows], columns=cols)
    if fresh.empty:
        return
    df = pd.concat([old[~old["symbol"].isin(list(rows_by_sym))], fresh], ignore_index=True)
    df = df[cols].sort_values(keys).reset_index(drop=True)
    tmp = path + ".tmp"
    df.to_csv(tmp, index=False)
    os.replace(tmp, path)


def load() -> pd.DataFrame:
    try:
        return pd.read_csv(CSV)
    except (OSError, ValueError):
        return pd.DataFrame(columns=COLS)


def save(df: pd.DataFrame) -> None:
    df = df[COLS].sort_values(["symbol", "fy"]).reset_index(drop=True)
    tmp = CSV + ".tmp"
    df.to_csv(tmp, index=False)
    os.replace(tmp, CSV)


def seed_from_cache() -> pd.DataFrame:
    from research.fundamentals_fetch import OUT
    rows = []
    for p in sorted(Path(OUT).glob("*.json")):
        if p.name.startswith("_"):
            continue
        d = json.loads(p.read_text(encoding="utf-8"))
        rows += rows_from_page(p.stem.split("~")[0], d)
    df = pd.DataFrame(rows, columns=COLS)
    save(df)
    print(f"seeded {df['symbol'].nunique():,} companies, {len(df):,} company-years -> {CSV}")
    seed_tables()
    return df


def seed_tables() -> None:
    """Only the two newer tables, from the research caches: the committed
    annual table keeps the cloud's newer rolling refreshes."""
    from research.fundamentals_fetch import OUT
    qrows = {}
    for p in sorted(Path(OUT).glob("*.json")):
        if not p.name.startswith("_"):
            qrows[p.stem.split("~")[0]] = q_rows_from_page(p.stem.split("~")[0], json.loads(p.read_text(encoding="utf-8")))
    _save_table(qrows, QTR_CSV, QTR_COLS, ["symbol", "qend"])
    from research.shareholding_fetch import OUT as SHP_DIR
    srows = {}
    for p in sorted(Path(SHP_DIR).glob("*.json")) if Path(SHP_DIR).exists() else []:
        if not p.name.startswith("_"):
            d = json.loads(p.read_text(encoding="utf-8"))
            srows[p.stem.split("~")[0]] = shp_rows_from_page(p.stem.split("~")[0], d)
    _save_table(srows, SHP_CSV, SHP_COLS, ["symbol", "kind", "period"])
    print(f"seeded quarters for {len(qrows):,} and shareholding for {len(srows):,} companies")


def universe() -> list[str]:
    """The liquid universe the radar saw last night (it records the list)."""
    try:
        with open(RADAR_STATE, encoding="utf-8") as f:
            return list(json.load(f).get("universe") or [])
    except (OSError, ValueError):
        return []


def refresh(per_run: int = PER_RUN, pause: float = 2.0) -> pd.DataFrame:
    from research.fundamentals_fetch import fetch
    df = load()
    uni = universe() or sorted(df["symbol"].unique())
    last = df.groupby("symbol")["fetched_at"].max() if len(df) else pd.Series(dtype=str)
    now = pd.Timestamp.now().normalize()
    age = {s: (now - pd.Timestamp(last[s])).days if s in last.index else 10**6 for s in uni}
    todo = [s for s in sorted(uni, key=lambda s: -age[s]) if age[s] >= STALE_DAYS][:per_run]
    print(f"{len(uni):,} companies in the universe; {len(todo)} stale to refresh this run", flush=True)
    new_rows, ok = [], 0
    shp_new, q_new = {}, {}
    for i, s in enumerate(todo, 1):
        d = fetch(s)
        if d:
            new_rows += rows_from_page(s, d)
            shp_new[s] = shp_rows_from_page(s, d)
            q_new[s] = q_rows_from_page(s, d)
            ok += 1
        if i % 50 == 0:
            print(f"  {i}/{len(todo)} fetched {ok}", flush=True)
        time.sleep(pause)
    _save_table(shp_new, SHP_CSV, SHP_COLS, ["symbol", "kind", "period"])
    _save_table(q_new, QTR_CSV, QTR_COLS, ["symbol", "qend"])
    if new_rows:
        fresh = pd.DataFrame(new_rows, columns=COLS)
        df = pd.concat([df[~df["symbol"].isin(fresh["symbol"].unique())], fresh], ignore_index=True)
        save(df)
    print(f"refreshed {ok} of {len(todo)}; table now {df['symbol'].nunique():,} companies")
    return df


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed-from-cache", action="store_true")
    ap.add_argument("--seed-tables", action="store_true", help="seed shareholding.csv and quarterly_results.csv only")
    ap.add_argument("--per-run", type=int, default=PER_RUN)
    a = ap.parse_args()
    if a.seed_tables:
        seed_tables()
    elif a.seed_from_cache:
        seed_from_cache()
    else:
        refresh(a.per_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
