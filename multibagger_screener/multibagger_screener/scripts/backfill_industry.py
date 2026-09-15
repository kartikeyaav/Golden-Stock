"""scripts/backfill_industry.py — the NSE industry label for names NSE's index
files never gave one.

WHY (2026-09-15, user-reported: "not all the values" in the screener). The 377
names added outside the indices arrived with no industry, because NSE publishes
that field only in index files. 192 were still blank on the screener, each
scored a flat 0.3 on the 15-point theme question, and none could be recognised
as a bank by the financial-sector checks. screener.in publishes the same NSE
label on every company page; this reads it once, politely, into a committed
label file that build_universe.py applies to blank industries only.

Idempotent and resumable: names already labelled are skipped, so a rerun only
fetches what is still missing.

    python scripts/backfill_industry.py            # fetch what is missing
    python scripts/backfill_industry.py --dry-run  # list who would be fetched
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from data.screener_fetch import _get, _parse_sector, nse_industry_label  # noqa: E402

LABELS = os.path.join(ROOT, "industry_labels.csv")
PAUSE_S = 1.8          # the same politeness the weekly fundamentals fetch keeps


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    uni = pd.read_csv(os.path.join(ROOT, "universe.csv"))
    known = {str(x) for x in uni["industry"].dropna() if str(x).strip()}
    blank = uni[uni["industry"].isna() | (uni["industry"].astype(str).str.strip() == "")]
    have = pd.read_csv(LABELS) if os.path.exists(LABELS) else pd.DataFrame(
        columns=["symbol", "industry", "screener_sector", "source_url", "fetched_at"])
    todo = [s for s in blank["symbol"] if s not in set(have["symbol"])]
    print(f"blank industries {len(blank)} | already labelled {len(blank) - len(todo)} | "
          f"to fetch {len(todo)}")
    if args.dry_run or not todo:
        return 0

    rows, missing, failed = [], [], []
    for i, sym in enumerate(todo, 1):
        url = None
        cache = os.path.join(ROOT, "fundamentals_cache", f"{sym}.json")
        if os.path.exists(cache):
            try:
                url = json.load(open(cache, encoding="utf-8")).get("source_url")
            except (OSError, ValueError):
                url = None
        url = url or f"https://www.screener.in/company/{sym}/consolidated/"
        try:
            sector = _parse_sector(_get(url))
        except Exception as e:  # noqa: BLE001 — one page must not stop the rest
            failed.append(sym)
            print(f"[{i}/{len(todo)}] FAIL {sym}: {str(e)[:60]}", flush=True)
            time.sleep(PAUSE_S)
            continue
        label = nse_industry_label(sector, known)
        if label:
            rows.append({"symbol": sym, "industry": label, "screener_sector": sector,
                         "source_url": url,
                         "fetched_at": datetime.now().isoformat(timespec="seconds")})
        else:
            missing.append(sym)
        if i % 25 == 0:
            print(f"[{i}/{len(todo)}] ...", flush=True)
        time.sleep(PAUSE_S)

    out = pd.concat([have, pd.DataFrame(rows)], ignore_index=True) if rows else have
    out = out.drop_duplicates(subset="symbol", keep="last")
    out.to_csv(LABELS, index=False)
    print(f"labelled {len(rows)} | no sector on page {len(missing)} | failed {len(failed)}"
          f" -> {LABELS} ({len(out)} labels total)")
    if missing:
        print("  no sector:", ", ".join(missing[:15]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
