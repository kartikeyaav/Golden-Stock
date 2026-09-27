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
    return df


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
    for i, s in enumerate(todo, 1):
        d = fetch(s)
        if d:
            new_rows += rows_from_page(s, d)
            ok += 1
        if i % 50 == 0:
            print(f"  {i}/{len(todo)} fetched {ok}", flush=True)
        time.sleep(pause)
    if new_rows:
        fresh = pd.DataFrame(new_rows, columns=COLS)
        df = pd.concat([df[~df["symbol"].isin(fresh["symbol"].unique())], fresh], ignore_index=True)
        save(df)
    print(f"refreshed {ok} of {len(todo)}; table now {df['symbol'].nunique():,} companies")
    return df


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed-from-cache", action="store_true")
    ap.add_argument("--per-run", type=int, default=PER_RUN)
    a = ap.parse_args()
    if a.seed_from_cache:
        seed_from_cache()
    else:
        refresh(a.per_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
