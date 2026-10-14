"""scripts/backfill_briefs.py - a one- or two-sentence description of every
company the app shows, from screener.in's "About" paragraph.

WHY (2026-10-14, user-requested): "upon opening each stock I want a brief on
what the stock is". Nothing in the data said what a company does. The weekly
fundamentals fetch now records the paragraph as it goes (screener_fetch
.parse_company_page "about"), but that only reaches the shortlist; this reads
it once for everything the app lists: the scanned universe, the multibagger
table and the penny screen.

screener.in rate-limits hard: on 2026-10-14 it answered HTTP 429 after about
16 requests in 10 minutes. So this runs slowly (7 s a request plus jitter),
backs off on 429 (90 s, doubling), stops cleanly after six refusals in a row,
and resumes where it left off. Run it from the laptop; it takes hours.

    python scripts/backfill_briefs.py            # fetch what is missing
    python scripts/backfill_briefs.py --dry-run  # count what would be fetched
    python scripts/backfill_briefs.py --retry-empty  # re-read pages that had none
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from data.screener_fetch import _get, _parse_about, _parse_name, company_brief  # noqa: E402

OUT = os.path.join(ROOT, "company_briefs.csv")
COLS = ["symbol", "company", "brief", "source_url", "fetched_at"]
PAUSE_S = 7.0
MAX_REFUSALS = 6


def wanted_symbols() -> list[str]:
    """What the app shows first, first: the top 60 of the multibagger table
    (Home's "Research these" and the Multibaggers tab open on them, and most
    sit outside the scanned universe, so they have no company name without
    this), then the scanned universe, then the rest of the table, then penny."""
    out: list[str] = []
    seen: set[str] = set()

    def add(seq):
        for s in seq:
            s = str(s).strip()
            if s and s not in seen and not s.startswith("DUMMY"):
                seen.add(s)
                out.append(s)

    ranked: list[str] = []
    radar_rows: list = []
    try:
        mb = json.load(open(os.path.join(ROOT, "state", "multibagger_radar.json"), encoding="utf-8"))
        stocks = (mb.get("mb") or {}).get("stocks") or {}
        ranked = sorted(stocks, key=lambda s: -(stocks[s].get("score") or 0))
        radar_rows = [r.get("sym") for r in mb.get("rows") or []]
    except (OSError, ValueError):
        pass
    add(ranked[:60])
    add(pd.read_csv(os.path.join(ROOT, "universe.csv"))["symbol"])
    add(ranked[60:])
    add(radar_rows)
    pr = os.path.join(ROOT, "penny_ranked.csv")
    if os.path.exists(pr):
        add(pd.read_csv(pr)["symbol"])
    return out


def load() -> pd.DataFrame:
    if os.path.exists(OUT):
        df = pd.read_csv(OUT, dtype=str, keep_default_na=False)
        for c in COLS:
            if c not in df.columns:
                df[c] = ""
        return df
    return pd.DataFrame(columns=COLS)


def save(df: pd.DataFrame) -> None:
    df = df.drop_duplicates(subset="symbol", keep="last").sort_values("symbol")
    tmp = OUT + ".tmp"
    df[COLS].to_csv(tmp, index=False)
    os.replace(tmp, OUT)


def fetch_about(sym: str) -> tuple[str | None, str | None, str]:
    """(about text or None, company name or None, url). Consolidated first,
    standalone on 404. The name matters for multibagger candidates outside the
    nightly scan, which otherwise reach the page as a bare symbol."""
    q = urllib.request.quote(sym, safe="")
    last = None
    for url in (f"https://www.screener.in/company/{q}/consolidated/",
                f"https://www.screener.in/company/{q}/"):
        try:
            page = _get(url)
            return _parse_about(page), _parse_name(page), url
        except urllib.error.HTTPError as e:
            if e.code == 404:
                last = e
                continue
            raise
    raise last or RuntimeError("no page")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--retry-empty", action="store_true")
    args = ap.parse_args()

    have = load()
    done = set(have["symbol"]) if not args.retry_empty else set(have.loc[have["brief"] != "", "symbol"])
    todo = [s for s in wanted_symbols() if s not in done]
    print(f"{len(have)} recorded | {len(todo)} to fetch", flush=True)
    if args.dry_run or not todo:
        return 0

    rows, refusals, wait, got, empty, failed = [], 0, 90, 0, 0, 0
    i = 0
    while i < len(todo):
        sym = todo[i]
        try:
            about, company, url = fetch_about(sym)
        except urllib.error.HTTPError as e:
            if e.code == 429:
                refusals += 1
                if refusals >= MAX_REFUSALS:
                    print(f"stopping: {refusals} refusals in a row (HTTP 429). Rerun later to resume.", flush=True)
                    break
                print(f"  429 on {sym}; waiting {wait}s", flush=True)
                time.sleep(wait)
                wait = min(wait * 2, 900)
                continue
            failed += 1
            print(f"  {sym}: HTTP {e.code}", flush=True)
            i += 1
            time.sleep(PAUSE_S)
            continue
        except Exception as e:  # noqa: BLE001 - one page must not stop the rest
            failed += 1
            print(f"  {sym}: {type(e).__name__} {str(e)[:60]}", flush=True)
            i += 1
            time.sleep(PAUSE_S)
            continue
        refusals, wait = 0, 90
        brief = company_brief(about)
        got += bool(brief)
        empty += not brief
        rows.append({"symbol": sym, "company": company or "", "brief": brief, "source_url": url,
                     "fetched_at": datetime.now().isoformat(timespec="seconds")})
        i += 1
        if len(rows) % 25 == 0:
            save(pd.concat([have, pd.DataFrame(rows)], ignore_index=True))
            print(f"[{i}/{len(todo)}] {got} briefs, {empty} without one, {failed} failed", flush=True)
        time.sleep(PAUSE_S + random.uniform(0, 2.5))

    if rows:
        save(pd.concat([have, pd.DataFrame(rows)], ignore_index=True))
    print(f"done this run: {got} briefs, {empty} pages without one, {failed} failed, "
          f"{len(todo) - i} left -> {OUT}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
