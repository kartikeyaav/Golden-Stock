"""
data/deals.py — NSE bulk and block deals, archived forward (2026-09-25).

WHY: the strategy review listed bulk/block deals as one of the two footprints
of heavy buying that small caps actually leave (options open interest does not
exist for most of this universe). A named institution taking 0.5%+ of a
company in one session is information the price chart cannot show.

SOURCE: nsearchives.nseindia.com/content/equities/{bulk,block}.csv — the
latest session only, unauthenticated (verified 2026-09-25: 237 bulk, 6 block).
NSE publishes no free back-file, so the archive ACCUMULATES FORWARD from the
first run, exactly like the filings archive. Committed nightly by daily.yml —
a file the cloud cannot persist does not exist.

THE CHURN RULE. Most bulk-deal rows in Indian small caps are proprietary
trading desks buying and selling the same stock in the same session: large
numbers that net to nothing. A client appearing on BOTH sides of the same
symbol on the same date is churn and is set aside (kept in the archive,
flagged, never summed). What remains is someone ending the day holding more,
or less, than they started with.

CONTEXT ONLY. Nothing here gates, ranks or sizes an entry (brief §2B). The
archive keeps every row with its date so a future study can ask, point in
time, whether alerts with named net buying did better — the only way it could
ever earn a weight.

    python data/deals.py          # fetch tonight's deals into the archive
"""

from __future__ import annotations

import io
import os
import sys
import time
import urllib.error
import urllib.request

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARCHIVE = os.path.join(ROOT, "deals_archive.csv")
URLS = {"bulk": "https://nsearchives.nseindia.com/content/equities/bulk.csv",
        "block": "https://nsearchives.nseindia.com/content/equities/block.csv"}
_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"),
    "Accept": "*/*", "Accept-Language": "en-US,en;q=0.9",
}
COLS = ["date", "symbol", "client", "side", "qty", "price", "kind"]
# wide enough for a one-year point-in-time study of the forward record,
# bounded so a nightly-committed CSV cannot grow without limit
RETENTION_DAYS = 400


def parse(raw: str, kind: str) -> pd.DataFrame:
    """NSE's CSV -> the archive schema. Tolerates the column-name drift NSE
    has shipped before (trailing spaces, 'Wght. Avg.' variants)."""
    if not raw or not raw.strip():
        return pd.DataFrame(columns=COLS)
    df = pd.read_csv(io.StringIO(raw))
    df.columns = [str(c).strip().lower() for c in df.columns]

    def col(*needles):
        for c in df.columns:
            if all(n in c for n in needles):
                return c
        return None
    need = {"date": col("date"), "symbol": col("symbol"), "client": col("client"),
            "side": col("buy"), "qty": col("quantity"), "price": col("price")}
    if any(v is None for v in need.values()):
        raise ValueError(f"unexpected {kind} columns: {list(df.columns)}")
    out = pd.DataFrame({
        "date": pd.to_datetime(df[need["date"]].astype(str).str.strip(), format="%d-%b-%Y",
                               errors="coerce").dt.strftime("%Y-%m-%d"),
        "symbol": df[need["symbol"]].astype(str).str.strip().str.upper(),
        "client": df[need["client"]].astype(str).str.strip().str.upper(),
        "side": df[need["side"]].astype(str).str.strip().str.upper(),
        "qty": pd.to_numeric(df[need["qty"]], errors="coerce"),
        "price": pd.to_numeric(df[need["price"]], errors="coerce"),
    })
    out["kind"] = kind
    return out.dropna(subset=["date", "qty", "price"])[COLS]


def fetch(kind: str, attempts: int = 3) -> pd.DataFrame:
    last = None
    for i in range(attempts):
        try:
            req = urllib.request.Request(URLS[kind], headers=_HEADERS)
            with urllib.request.urlopen(req, timeout=40) as r:
                return parse(r.read().decode("utf-8", "replace"), kind)
        except (urllib.error.URLError, TimeoutError, ValueError, OSError) as e:
            last = e
            time.sleep(2 * (i + 1))
    raise RuntimeError(f"{kind} deals unavailable: {last}")


def load() -> pd.DataFrame:
    if not os.path.exists(ARCHIVE):
        return pd.DataFrame(columns=COLS)
    try:
        return pd.read_csv(ARCHIVE, dtype={"symbol": str, "client": str})
    except (OSError, ValueError):
        return pd.DataFrame(columns=COLS)


def update(frames: list[pd.DataFrame], today: str | None = None) -> tuple[pd.DataFrame, int]:
    """Merge fetched rows into the archive: dedupe, prune past retention."""
    old = load()
    parts = [x for x in [old, *frames] if x is not None and len(x)]
    if not parts:
        return pd.DataFrame(columns=COLS), 0
    new = pd.concat(parts, ignore_index=True)
    new = new.drop_duplicates(subset=COLS, keep="first")
    cutoff = (pd.Timestamp(today or pd.Timestamp.now()) - pd.Timedelta(days=RETENTION_DAYS)).strftime("%Y-%m-%d")
    new = new[new["date"] >= cutoff].sort_values(["date", "symbol", "client", "side"])
    return new.reset_index(drop=True), len(new) - len(old)


def with_churn_flag(df: pd.DataFrame) -> pd.DataFrame:
    """Flag rows where the same client both bought and sold the same symbol
    on the same date — intraday churn, which nets to nothing."""
    if df.empty:
        return df.assign(churn=pd.Series(dtype=bool))
    sides = df.groupby(["date", "symbol", "client"])["side"].transform(lambda s: s.nunique())
    return df.assign(churn=sides > 1)


def net_by_symbol(df: pd.DataFrame, since: str) -> pd.DataFrame:
    """Per symbol, from `since`: net value bought by non-churn clients (Rs),
    gross buy / sell value, and the largest named buyers."""
    d = with_churn_flag(df[df["date"] >= since])
    d = d[~d["churn"]]
    if d.empty:
        return pd.DataFrame(columns=["symbol", "net_value", "buy_value", "sell_value", "buyers", "deals"])
    d = d.assign(value=d["qty"] * d["price"],
                 signed=lambda x: x["qty"] * x["price"] * x["side"].map({"BUY": 1, "SELL": -1}).fillna(0))
    rows = []
    for sym, g in d.groupby("symbol"):
        buys = g[g["side"] == "BUY"].groupby("client")["value"].sum().sort_values(ascending=False)
        rows.append({"symbol": sym, "net_value": round(float(g["signed"].sum()), 0),
                     "buy_value": round(float(g.loc[g["side"] == "BUY", "value"].sum()), 0),
                     "sell_value": round(float(g.loc[g["side"] == "SELL", "value"].sum()), 0),
                     "buyers": [c for c in buys.index[:3]], "deals": int(len(g))})
    return pd.DataFrame(rows)


def watched_symbols() -> set[str] | None:
    """The main universe plus the penny universe. Only these names are kept:
    unfiltered, NSE's ~240 rows a night would commit ~9 MB a year into the
    repository. None when neither file is readable — then nothing is dropped,
    because dropping on a read failure would lose data for good."""
    syms: set[str] = set()
    for name in ("universe.csv", "penny_universe.csv"):
        p = os.path.join(ROOT, name)
        try:
            syms |= set(pd.read_csv(p, usecols=["symbol"])["symbol"].astype(str).str.upper())
        except (OSError, ValueError, KeyError):
            continue
    return syms or None


def main() -> None:
    frames, errors = [], []
    for kind in ("bulk", "block"):
        try:
            frames.append(fetch(kind))
        except RuntimeError as e:
            errors.append(str(e))
    if not frames:
        print("deals: nothing fetched — " + "; ".join(errors))
        sys.exit(0)                               # non-fatal by contract
    keep = watched_symbols()
    if keep is not None:
        frames = [f[f["symbol"].isin(keep)] for f in frames]
    merged, added = update(frames)
    tmp = ARCHIVE + ".tmp"
    merged.to_csv(tmp, index=False)
    os.replace(tmp, ARCHIVE)
    latest = max((f["date"].max() for f in frames if len(f)), default="—")
    print(f"deals: +{added} rows (session {latest}); archive {len(merged)} rows"
          + (f"; errors: {'; '.join(errors)}" if errors else ""))


if __name__ == "__main__":
    main()
