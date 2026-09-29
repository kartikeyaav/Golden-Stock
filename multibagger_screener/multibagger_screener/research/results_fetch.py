"""
research/results_fetch.py — every quarterly result each company filed with
NSE since 2016, for family Q of PREREG_2026-09-29_multibagger_factors.md
(CAN SLIM's "C": the latest quarter against the same quarter a year before).

NSE lists each company's filings at /api/corporates-financial-results; every
filing links an XBRL file on nsearchives (~30 KB) whose "OneD" context is the
quarter itself. One filing per quarter is kept, consolidated where the
company files one. What is stored per quarter is small:

    end, start, filed (the exchange's broadcast time: the moment it became
    public), nature, revenue, profit, eps  (rupees; EPS per share)

Written to ~/golden_stock_data/results/{SYMBOL}.json, resumable.

    python -m research.results_fetch [--limit N] [--workers 6]
"""

from __future__ import annotations

import argparse
import json
import re
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

from data.insider import Session, _xml
from data.nse_history import HIST_DIR

SRC = HIST_DIR.parent / "screener"
OUT = HIST_DIR.parent / "results"
API = "https://www.nseindia.com/api/corporates-financial-results?index=equities&symbol={sym}&period=Quarterly"
REV = ("RevenueFromOperations", "InterestEarned", "TotalRevenueFromOperations", "NetSalesIncomeFromOperations", "Income", "TotalIncome")
PAT = ("ProfitLossForPeriod", "NetProfitLossForThePeriod", "ProfitLossForThePeriod", "ProfitLossFromOrdinaryActivitiesAfterTax")
EPS = ("BasicEarningsLossPerShareFromContinuingAndDiscontinuedOperations", "BasicEarningsLossPerShareFromContinuingOperations",
       "BasicEarningsPerShareAfterExtraordinaryItems", "BasicEarningsPerShareBeforeExtraordinaryItems")


def _when(s: str) -> str | None:
    for fmt in ("%d-%b-%Y %H:%M:%S", "%d-%b-%Y %H:%M", "%d-%b-%Y"):
        try:
            return datetime.strptime(str(s).strip(), fmt).isoformat(timespec="seconds")
        except ValueError:
            continue
    return None


def pick(filings: list[dict]) -> list[dict]:
    """One filing per quarter end: consolidated if filed, and its FIRST
    broadcast (the moment the numbers became public; a later revision would
    be look-ahead). Filings without an XBRL file (NSE's "-", common before
    2018) are skipped."""
    by: dict[str, dict] = {}
    for f in filings:
        end = _when(f.get("toDate") or "")
        filed = _when(f.get("broadCastDate") or f.get("filingDate") or "")
        url = str(f.get("xbrl") or "")
        if not end or not filed or not url.endswith(".xml") or str(f.get("cumulative", "")).lower().startswith("cumulative"):
            continue
        cons = str(f.get("consolidated", "")).lower().startswith("consolidated")
        key = end[:10]
        cur = by.get(key)
        rank = (not cons, filed)                      # consolidated first, then earliest
        if cur is None or rank < cur["_rank"]:
            by[key] = {"end": key, "filed": filed, "consolidated": cons, "xbrl": url, "_rank": rank}
    return [dict((k, v) for k, v in r.items() if k != "_rank") for r in sorted(by.values(), key=lambda r: r["end"])]


def _first(x: str, names: tuple[str, ...], ctx: str = "OneD") -> float | None:
    for n in names:
        m = re.search(rf'<in-bse-fin:{n}\s+contextRef="{ctx}"[^>]*>\s*([-\d.eE+]+)\s*<', x)
        if m:
            try:
                return float(m.group(1))
            except ValueError:
                continue
    return None


def parse(x: str) -> dict:
    start = re.search(r'<in-bse-fin:DateOfStartOfReportingPeriod\s+contextRef="OneD"[^>]*>([^<]+)<', x)
    end = re.search(r'<in-bse-fin:DateOfEndOfReportingPeriod\s+contextRef="OneD"[^>]*>([^<]+)<', x)
    return {"start": start.group(1).strip() if start else None, "end_x": end.group(1).strip() if end else None,
            "revenue": _first(x, REV), "profit": _first(x, PAT), "eps": _first(x, EPS)}


def one(sess: Session, sym: str, workers: int) -> dict | None:
    base = sym.split("~")[0]
    try:
        data = sess.get_json(API.format(sym=base))
    except Exception:  # noqa: BLE001
        return None
    rows = pick(data if isinstance(data, list) else (data or {}).get("data", []))
    rows = [r for r in rows if r["end"] >= "2015-06-30"]

    def get(r):
        try:
            return {**r, **parse(_xml(r["xbrl"]))}
        except Exception:  # noqa: BLE001
            return {**r, "error": True}
    with ThreadPoolExecutor(workers) as ex:
        out = list(ex.map(get, rows))
    return {"symbol": sym, "fetched_at": datetime.now().isoformat(timespec="seconds"), "quarters": out}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--pause", type=float, default=1.0)
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    syms = sorted(p.stem for p in SRC.glob("*.json") if not p.name.startswith("_"))
    miss_p = OUT / "_missing.json"
    missing = json.loads(miss_p.read_text()) if miss_p.exists() else {}
    todo = [s for s in syms if not (OUT / f"{s}.json").exists() and s not in missing]
    if a.limit:
        todo = todo[: a.limit]
    print(f"{len(todo)} to fetch ({len(syms)} in the research universe) -> {OUT}", flush=True)
    sess = Session(pause=1.0)
    ok = 0
    for i, s in enumerate(todo, 1):
        d = one(sess, s, a.workers)
        if d and d["quarters"]:
            (OUT / f"{s}.json").write_text(json.dumps(d), encoding="utf-8")
            ok += 1
        else:
            missing[s] = datetime.now().isoformat(timespec="seconds")
        if i % 25 == 0 or i == len(todo):
            miss_p.write_text(json.dumps(missing), encoding="utf-8")
            print(f"{i}/{len(todo)} ok {ok} missing {len(missing)}", flush=True)
        time.sleep(a.pause)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
