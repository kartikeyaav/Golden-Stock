"""
data/insider.py — promoter and insider trades (SEBI PIT Regulation 7(2)
disclosures) from NSE, 2015 onward.

WHY. Of every "smart money" footprint, insiders buying their own stock is the
one with published Indian evidence (large insider purchases: +6.67% abnormal
return over 90 days, stronger for promoters and small caps — DECISION 2026,
Springer). The research program (PREREG_2026-09-26) listed it as the strongest
untapped source.

TWO ERAS (found 2026-09-27):
  * to ~May 2026: /api/corporates-pit — one JSON record per disclosure with
    person category, mode (Market Purchase/Sale, Pledge, ESOP, ...), quantity,
    rupee value, holding % before/after, and the exchange DISCLOSURE timestamp;
  * from ~May 2026: /api/corporates-pit-gg — a list of XBRL filings; each
    filing's XML (on nsearchives, no session needed) carries one or more
    disclosures with the same facts.
Both need an nseindia.com session: the home page answers 403, the insider
page itself sets the cookies.

POINT IN TIME: a trade is known when the EXCHANGE disseminated it
(`disclosed_at`), not when it happened — that is the only timestamp a signal
may use.

    python data/insider.py backfill [--start 2015-06]   # research history (laptop)
    python data/insider.py recent [--days 10]            # the live tail
"""

from __future__ import annotations

import argparse
import gzip
import http.cookiejar
import io
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from data.nse_history import HIST_DIR  # noqa: E402

RESEARCH_PATH = HIST_DIR.parent / "insider" / "insider_trades.csv.gz"
ARCHIVE = os.path.join(ROOT, "insider_archive.csv")        # the live, committed tail
ARCHIVE_DAYS = 400
PAGE = "https://www.nseindia.com/companies-listing/corporate-filings-insider-trading"
OLD_API = "https://www.nseindia.com/api/corporates-pit?index=equities&from_date={a}&to_date={b}"
NEW_API = "https://www.nseindia.com/api/corporates-pit-gg?index=equities&from_date={a}&to_date={b}"
COLS = ["disclosed_at", "symbol", "company", "person", "category", "txn", "mode", "qty", "value",
        "pct_before", "pct_after", "trade_from", "trade_to", "source", "key"]
_H = {"User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                     "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"),
      "Accept": "application/json, text/plain, */*", "Accept-Language": "en-US,en;q=0.9",
      "Referer": PAGE}


class Session:
    """An nseindia.com session primed from the insider page (the home page is
    refused); re-primed once when the API starts refusing."""

    def __init__(self, pause: float = 1.5):
        self.cj = http.cookiejar.CookieJar()
        self.op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.cj))
        self.pause = pause
        self.prime()

    def prime(self) -> None:
        req = urllib.request.Request(PAGE, headers={**_H, "Accept": "text/html"})
        self.op.open(req, timeout=30).read()
        time.sleep(self.pause)

    def get_json(self, url: str):
        for attempt in range(3):
            try:
                with self.op.open(urllib.request.Request(url, headers=_H), timeout=40) as r:
                    return json.loads(r.read())
            except urllib.error.HTTPError as e:
                if e.code in (401, 403) and attempt < 2:
                    time.sleep(3 * (attempt + 1))
                    self.prime()
                    continue
                raise
            except (urllib.error.URLError, TimeoutError):
                time.sleep(3 * (attempt + 1))
        raise RuntimeError(f"NSE refused {url}")

    def get_text(self, url: str) -> str:
        with self.op.open(urllib.request.Request(url, headers={**_H, "Accept": "*/*"}), timeout=40) as r:
            return r.read().decode("utf-8", "replace")


# ---------------------------------------------------------------------------
# normalisation
# ---------------------------------------------------------------------------

def _cat(raw: str) -> str:
    s = (raw or "").strip().lower()
    if s.startswith("promoter group"):
        return "promoter_group"
    if s.startswith("promoter"):
        return "promoter"
    if "director" in s:
        return "director"
    if "key managerial" in s or s == "kmp":
        return "kmp"
    if "employee" in s:
        return "employee"
    if "immediate relative" in s:
        return "relative"
    return "other"


def _txn(raw: str) -> str:
    s = (raw or "").strip().lower()
    if s in ("buy", "acquisition"):
        return "buy"
    if s in ("sell", "sale", "disposal"):
        return "sell"
    if "revoke" in s:
        return "pledge_revoke"
    if "invoke" in s:
        return "pledge_invoke"
    if "pledge" in s:
        return "pledge"
    return s or "other"


def _num(x) -> float | None:
    try:
        v = float(str(x).replace(",", "").strip())
        return v
    except (TypeError, ValueError):
        return None


def _dt(s: str, fmts=("%d-%b-%Y %H:%M:%S", "%d-%b-%Y %H:%M", "%d-%b-%Y", "%Y-%m-%d")):
    s = (s or "").strip()
    for f in fmts:
        try:
            return datetime.strptime(s, f)
        except ValueError:
            continue
    return None


def normalise_old(r: dict) -> dict:
    return {
        "disclosed_at": _dt(r.get("date")), "symbol": (r.get("symbol") or "").strip(),
        "company": r.get("company"), "person": r.get("acqName"),
        "category": _cat(r.get("personCategory")), "txn": _txn(r.get("tdpTransactionType")),
        "mode": (r.get("acqMode") or "").strip(), "qty": _num(r.get("secAcq")),
        "value": _num(r.get("secVal")), "pct_before": _num(r.get("befAcqSharesPer")),
        "pct_after": _num(r.get("afterAcqSharesPer")), "trade_from": _dt(r.get("acqfromDt")),
        "trade_to": _dt(r.get("acqtoDt")), "source": "pit", "key": f"pit:{r.get('did')}:{r.get('pid')}",
    }


def parse_xbrl(xml: str, meta: dict) -> list[dict]:
    """Every DisclosureN context in one filing -> normalised rows."""
    facts: dict[str, dict[str, str]] = {}
    for name, ctx, val in re.findall(r"<(?:[A-Za-z0-9\-]+:)?([A-Za-z0-9]+)[^>]*contextRef=\"([^\"]+)\"[^>]*>([^<]*)</", xml):
        facts.setdefault(ctx, {})[name] = val.strip()
    main = facts.get("MainI", {})
    out = []
    for ctx, f in facts.items():
        if not ctx.startswith("Disclosure"):
            continue
        pb, pa = _num(f.get("SecuritiesHeldPriorToAcquisitionOrDisposalPercentageOfShareholding")), \
            _num(f.get("SecuritiesHeldPostAcquistionOrDisposalPercentageOfShareholding"))
        # the XBRL states holdings as a FRACTION (0.6349); the old feed as a percent (63.49)
        pb = pb * 100 if pb is not None and pb <= 1.0 else pb
        pa = pa * 100 if pa is not None and pa <= 1.0 else pa
        out.append({
            "disclosed_at": _dt(meta.get("broadcastDateTime")) or _dt(main.get("DateOfFiling")),
            "symbol": (main.get("Symbol") or meta.get("symbol") or "").strip(),
            "company": main.get("NameOfTheCompany") or meta.get("companyName"),
            "person": f.get("NameOfThePerson"), "category": _cat(f.get("CategoryOfPerson")),
            "txn": _txn(f.get("SecuritiesAcquiredOrDisposedTransactionType")),
            "mode": (f.get("ModeOfAcquisitionOrDisposal") or "").strip(),
            "qty": _num(f.get("SecuritiesAcquiredOrDisposedNumberOfSecurity")),
            "value": _num(f.get("SecuritiesAcquiredOrDisposedValueOfSecurity")),
            "pct_before": pb, "pct_after": pa,
            "trade_from": _dt(f.get("DateOfAllotmentAdviceOrAcquisitionOfSharesOrSaleOfSharesSpecifyFromDate")),
            "trade_to": _dt(f.get("DateOfAllotmentAdviceOrAcquisitionOfSharesOrSaleOfSharesSpecifyToDate")),
            "source": "xbrl", "key": f"xbrl:{meta.get('appId')}:{ctx}",
        })
    return out


# ---------------------------------------------------------------------------
# fetching
# ---------------------------------------------------------------------------

def _fmt(d: date) -> str:
    return d.strftime("%d-%m-%Y")


def fetch_old(s: Session, a: date, b: date) -> list[dict]:
    j = s.get_json(OLD_API.format(a=_fmt(a), b=_fmt(b)))
    return [normalise_old(r) for r in (j.get("data") or [])]


def fetch_new(s: Session, a: date, b: date, pause: float = 0.15, verbose: bool = False) -> list[dict]:
    """The XBRL era, fetched a WEEK at a time: the list endpoint answers a
    month-long range slowly (a backfill sat on one month for 50 minutes), and
    a week keeps each call short and each failure small."""
    rows, bad = [], 0
    d = a
    while d <= b:
        e = min(d + timedelta(days=6), b)
        j = s.get_json(NEW_API.format(a=_fmt(d), b=_fmt(e)))
        lst = [m for m in (j.get("data") or []) if str(m.get("xmlFileName") or "").endswith(".xml")]
        for meta in lst:
            try:
                rows += parse_xbrl(s.get_text(meta["xmlFileName"]), meta)
            except Exception:  # noqa: BLE001 — one unreadable filing never stops the rest
                bad += 1
            time.sleep(pause)
        if verbose:
            print(f"    {d:%Y-%m-%d}..{e:%m-%d}: {len(lst)} filings, {len(rows)} disclosures so far"
                  + (f", {bad} unreadable" if bad else ""), flush=True)
        d = e + timedelta(days=1)
    return rows


def _months(start: date, end: date):
    d = date(start.year, start.month, 1)
    while d <= end:
        nxt = date(d.year + (d.month == 12), d.month % 12 + 1, 1)
        yield d, min(nxt - timedelta(days=1), end)
        d = nxt


def to_frame(rows: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(rows, columns=COLS)
    if df.empty:
        return df
    df = df.drop_duplicates("key")
    # the two eras overlap around the switch: the same trade can appear in both
    df = df.sort_values(["disclosed_at", "source"]).drop_duplicates(
        ["symbol", "person", "txn", "qty", "trade_from"], keep="first")
    return df.sort_values("disclosed_at").reset_index(drop=True)


def backfill(start: date, end: date, switch: date = date(2026, 4, 1)) -> pd.DataFrame:
    """The whole history: the old feed month by month to the switch, then the
    XBRL feed. Cached per month so an interrupted run resumes."""
    cache = RESEARCH_PATH.parent / "months"
    cache.mkdir(parents=True, exist_ok=True)
    s = Session()
    for a, b in _months(start, end):
        p = cache / f"{a:%Y-%m}.json.gz"
        if p.exists() and b < date.today() - timedelta(days=7):
            continue
        rows = fetch_old(s, a, b) if a < date(2026, 6, 1) else []
        if a >= switch:
            rows += fetch_new(s, a, b, verbose=True)
        p.write_bytes(gzip.compress(json.dumps(rows, default=str).encode()))
        print(f"{a:%Y-%m}: {len(rows):5} disclosures", flush=True)
        time.sleep(s.pause)
    allrows = []
    for p in sorted(cache.glob("*.json.gz")):
        allrows += json.loads(gzip.decompress(p.read_bytes()))
    df = to_frame(allrows)
    df.to_csv(RESEARCH_PATH, index=False, compression="gzip")
    print(f"insider history: {len(df):,} disclosures {df['disclosed_at'].min()} -> "
          f"{df['disclosed_at'].max()} -> {RESEARCH_PATH}")
    return df


def recent(days: int = 10) -> pd.DataFrame:
    """The live tail: the last `days` of XBRL filings merged into the committed
    archive, which keeps ARCHIVE_DAYS of promoter / director / KMP trades."""
    s = Session()
    end = date.today()
    new = to_frame(fetch_new(s, end - timedelta(days=days), end))
    try:
        old = pd.read_csv(ARCHIVE, parse_dates=["disclosed_at", "trade_from", "trade_to"])
    except (OSError, ValueError):
        old = pd.DataFrame(columns=COLS)
    df = to_frame(pd.concat([old, new], ignore_index=True).to_dict("records"))
    keep = df["category"].isin(["promoter", "promoter_group", "director", "kmp"])
    cutoff = pd.Timestamp(end - timedelta(days=ARCHIVE_DAYS))
    df = df[keep & (pd.to_datetime(df["disclosed_at"]) >= cutoff)]
    df.to_csv(ARCHIVE, index=False)
    print(f"insider archive: {len(df):,} rows (+{len(new):,} fetched over {days} days) -> {ARCHIVE}")
    return df


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("backfill")
    b.add_argument("--start", default="2015-06-01")
    r = sub.add_parser("recent")
    r.add_argument("--days", type=int, default=10)
    a = ap.parse_args()
    if a.cmd == "backfill":
        backfill(date.fromisoformat(a.start), date.today())
    else:
        recent(a.days)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
