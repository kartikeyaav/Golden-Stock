"""scripts/bhavcopy_compare.py — measure the NSE bhavcopy against the cached
Yahoo prices, for PREREG_2026-09-12_bhavcopy.md.

Measurement only: reads the bhavcopy cache and the local price cache, writes
nothing but its own report. The criteria it is judged against were fixed in the
pre-registration BEFORE this ran.

    python scripts/bhavcopy_compare.py            # last 5 sessions
    python scripts/bhavcopy_compare.py --sessions 10
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import date, timedelta

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from data.nse_all import bhavcopy  # noqa: E402

CACHE = os.path.join(ROOT, "data_cache")

# the bhavcopy's column names differ across NSE's old and UDiFF formats
SYM_COLS = ("symbol", "tckrsymb", "sc_code")
CLOSE_COLS = ("close", "clspric", "close_price", "cls_pric")
SERIES_COLS = ("series", "sctysrs")


def _col(df: pd.DataFrame, names) -> str | None:
    lower = {c.lower().replace("_", ""): c for c in df.columns}
    for n in names:
        key = n.lower().replace("_", "")
        if key in lower:
            return lower[key]
    return None


def sessions(n: int) -> list[date]:
    out, d = [], date.today()
    while len(out) < n and (date.today() - d).days < 30:
        if d.weekday() < 5:
            bh = bhavcopy(d)
            if bh is not None and len(bh):
                out.append(d)
        d -= timedelta(days=1)
    return out


def cached_close(symbol: str, day: date) -> float | None:
    path = os.path.join(CACHE, f"{symbol}.csv")
    if not os.path.exists(path):
        return None
    try:
        df = pd.read_csv(path, usecols=["date", "close"])
    except (ValueError, OSError):
        return None
    hit = df[df["date"].astype(str).str[:10] == day.isoformat()]
    return float(hit["close"].iloc[-1]) if len(hit) else None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sessions", type=int, default=5)
    args = ap.parse_args()

    uni = pd.read_csv(os.path.join(ROOT, "universe.csv"))
    watched = list(uni["symbol"])
    days = sessions(args.sessions)
    print(f"universe {len(watched)} · sessions tested: "
          f"{', '.join(d.isoformat() for d in days)}\n")

    print(f"{'session':<12}{'rows':>7}{'EQ':>7}{'matched':>9}{'coverage':>10}"
          f"{'compared':>10}{'within .5%':>12}{'agreement':>11}")
    c1_worst, c2_worst, retrieved = 100.0, 100.0, 0
    for d in days:
        bh = bhavcopy(d)
        if bh is None or not len(bh):
            print(f"{d.isoformat():<12}   NOT RETRIEVABLE")
            continue
        retrieved += 1
        scol, ccol, sercol = _col(bh, SYM_COLS), _col(bh, CLOSE_COLS), _col(bh, SERIES_COLS)
        if not scol or not ccol:
            print(f"{d.isoformat():<12}   columns not recognised: {list(bh.columns)[:8]}")
            continue
        b = bh.copy()
        b[scol] = b[scol].astype(str).str.strip()
        if sercol:
            b = b[b[sercol].astype(str).str.strip() == "EQ"]
        closes = dict(zip(b[scol], pd.to_numeric(b[ccol], errors="coerce")))
        matched = [s for s in watched if s in closes]
        cov = 100.0 * len(matched) / len(watched)

        compared = within = 0
        for s in matched:
            y = cached_close(s, d)
            if y is None or not y:
                continue
            n = closes[s]
            if pd.isna(n):
                continue
            compared += 1
            if abs(n - y) / y <= 0.005:
                within += 1
        agree = 100.0 * within / compared if compared else float("nan")
        c1_worst = min(c1_worst, cov)
        if compared:
            c2_worst = min(c2_worst, agree)
        print(f"{d.isoformat():<12}{len(bh):>7}{len(b):>7}{len(matched):>9}"
              f"{cov:>9.1f}%{compared:>10}{within:>12}{agree:>10.1f}%")

    print(f"\nC1 coverage   worst session {c1_worst:.1f}%   bar >= 98%    "
          f"{'PASS' if c1_worst >= 98 else 'FAIL'}")
    print(f"C2 agreement  worst session {c2_worst:.1f}%   bar >= 99%    "
          f"{'PASS' if c2_worst >= 99 else 'FAIL'}")
    print(f"C3 timeliness {retrieved} of {len(days)} retrieved  bar 5 of 5   "
          f"{'PASS' if retrieved >= min(5, args.sessions) else 'FAIL'}")
    print("C4 adjustment safety — see tests/test_bhavcopy_seam.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
