"""
research/fundamentals_fetch.py — annual statements for the value hypotheses
(H18-H20 of PREREG_2026-09-26), for every company that was ever in the
point-in-time universe, into a RESEARCH cache outside the repo.

Uses the live parser (data/screener_fetch.py) with the extra sections the
value tests need — annual P&L, the full cash-flow statement (investing flows
stand in for capex), total assets, ROCE — and never writes the live
fundamentals_cache the scan reads.

SURVIVORSHIP: screener.in serves pages for companies listed today; a company
that was delisted or merged away usually has none. Every fundamental result
must report how much of the universe it could not see
(research/fundamentals.py does).

    python -m research.fundamentals_fetch [--limit N] [--pause 2.5]
"""

from __future__ import annotations

import argparse
import json
import os
import time
from datetime import datetime
from pathlib import Path

from data import screener_fetch as SF
from data.nse_history import HIST_DIR

OUT = HIST_DIR.parent / "screener"


def parse(html: str) -> dict:
    return {
        "top_ratios": SF._parse_top_ratios(html),
        "profit_loss": SF._parse_data_table(html, "profit-loss",
                                            ["Sales", "Revenue", "Operating Profit", "OPM %",
                                             "Financing Profit", "Net Profit", "EPS in Rs"]),
        "balance_sheet": SF._parse_data_table(html, "balance-sheet",
                                              ["Equity Capital", "Reserves", "Borrowings",
                                               "Total Liabilities", "Total Assets"]),
        "cash_flow": SF._parse_data_table(html, "cash-flow",
                                          ["Cash from Operating Activity",
                                           "Cash from Investing Activity",
                                           "Cash from Financing Activity"]),
        "ratios": SF._parse_data_table(html, "ratios", ["ROCE %", "ROE %"]),
        "quarters": SF._parse_data_table(html, "quarters",
                                         ["Sales", "Revenue", "Operating Profit", "Net Profit",
                                          "EPS in Rs"]),
    }


def fetch(symbol: str) -> dict | None:
    base = symbol.split("~")[0]                       # reused-symbol suffix is ours, not NSE's
    q = SF.urllib.request.quote(base, safe="")
    for url in (f"https://www.screener.in/company/{q}/consolidated/",
                f"https://www.screener.in/company/{q}/"):
        try:
            html = SF._get(url)
        except Exception:  # noqa: BLE001
            continue
        d = parse(html)
        if (d["profit_loss"] or {}).get("rows"):
            d.update(symbol=symbol, source_url=url,
                     fetched_at=datetime.now().isoformat(timespec="seconds"))
            return d
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbols", default=str(OUT / "_symbols.txt"))
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--pause", type=float, default=2.5)
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    syms = [s.strip() for s in open(a.symbols, encoding="utf-8") if s.strip()]
    miss_p = OUT / "_missing.json"
    missing = json.loads(miss_p.read_text()) if miss_p.exists() else {}
    todo = [s for s in syms if not (OUT / f"{s}.json").exists() and s not in missing]
    if a.limit:
        todo = todo[: a.limit]
    print(f"{len(todo)} to fetch ({len(syms)} listed) -> {OUT}", flush=True)
    ok = 0
    for i, s in enumerate(todo, 1):
        d = fetch(s)
        if d:
            (OUT / f"{s}.json").write_text(json.dumps(d), encoding="utf-8")
            ok += 1
        else:
            missing[s] = datetime.now().isoformat(timespec="seconds")
        if i % 50 == 0 or i == len(todo):
            miss_p.write_text(json.dumps(missing), encoding="utf-8")
            print(f"{i}/{len(todo)} ok {ok} missing {len(missing)}", flush=True)
        time.sleep(a.pause)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
