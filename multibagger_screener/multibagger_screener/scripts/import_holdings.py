"""
scripts/import_holdings.py — update holdings.csv from a Zerodha Console export,
NO daily Kite login required (SEBI kills API sessions every morning; the
Console CSV never expires).

How to get the file:
  console.zerodha.com -> Portfolio -> Holdings -> download (CSV). Then:

    python scripts/import_holdings.py ~/Downloads/holdings.csv
    python scripts/import_holdings.py ~/Downloads/holdings.csv --dry-run

Robust to Console's format drift: skips preamble lines, finds the header row
by keyword, and maps the symbol / quantity / average-price columns fuzzily.
Writes holdings.csv (symbol,quantity,avg_price). Does NOT touch positions.csv
— seed/manage those deliberately (a holding is not automatically a managed
two-lot position). Prints a diff so you see exactly what changed.
"""

from __future__ import annotations

import argparse
import csv
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOLDINGS = os.path.join(ROOT, "holdings.csv")

# header keyword -> which field (first match wins, case-insensitive substring)
_SYMBOL_KEYS = ("symbol", "tradingsymbol", "instrument")
_QTY_KEYS = ("quantity available", "quantity", "qty", "net quantity")
_AVG_KEYS = ("average price", "avg. cost", "avg cost", "average cost", "buy avg")


def _find(headers: list[str], keys: tuple[str, ...]) -> int | None:
    low = [h.strip().lower() for h in headers]
    for k in keys:                       # exact-ish match first
        for i, h in enumerate(low):
            if h == k:
                return i
    for k in keys:                       # then substring
        for i, h in enumerate(low):
            if k in h:
                return i
    return None


def parse_console_csv(path: str) -> list[dict]:
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        reader = list(csv.reader(f))
    # find the header row: the first row that has a symbol column AND a qty column
    header_idx = None
    for i, row in enumerate(reader):
        if _find(row, _SYMBOL_KEYS) is not None and _find(row, _QTY_KEYS) is not None:
            header_idx = i
            break
    if header_idx is None:
        raise ValueError("could not locate a header row with Symbol + Quantity columns")
    headers = reader[header_idx]
    si, qi, ai = (_find(headers, _SYMBOL_KEYS), _find(headers, _QTY_KEYS), _find(headers, _AVG_KEYS))
    if ai is None:
        raise ValueError("could not find an average-price column in the export")

    out = []
    for row in reader[header_idx + 1:]:
        if not row or si >= len(row) or not row[si].strip():
            continue
        sym = row[si].strip().upper()
        try:
            qty = int(float(row[qi].replace(",", "")))
            avg = round(float(row[ai].replace(",", "")), 3)
        except (ValueError, IndexError):
            continue
        if qty > 0 and avg > 0:
            out.append({"symbol": sym, "quantity": qty, "avg_price": avg})
    return out


def load_current() -> dict[str, dict]:
    if not os.path.exists(HOLDINGS):
        return {}
    with open(HOLDINGS, "r", encoding="utf-8", newline="") as f:
        return {r["symbol"]: r for r in csv.DictReader(f)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("csv_path", help="Zerodha Console holdings export (.csv)")
    ap.add_argument("--dry-run", action="store_true", help="print the diff, write nothing")
    args = ap.parse_args()
    if not os.path.exists(args.csv_path):
        print(f"file not found: {args.csv_path}")
        sys.exit(1)

    new = parse_console_csv(args.csv_path)
    if not new:
        print("no holdings parsed — is this a Console holdings export?")
        sys.exit(1)
    new_by = {h["symbol"]: h for h in new}
    old_by = load_current()

    added = [s for s in new_by if s not in old_by]
    removed = [s for s in old_by if s not in new_by]
    changed = [s for s in new_by if s in old_by and
               (str(new_by[s]["quantity"]) != str(old_by[s].get("quantity"))
                or abs(float(new_by[s]["avg_price"]) - float(old_by[s].get("avg_price", 0))) > 0.01)]

    print(f"parsed {len(new)} holdings from export")
    for s in added:
        print(f"  + ADD    {s}: {new_by[s]['quantity']} @ {new_by[s]['avg_price']}")
    for s in changed:
        print(f"  ~ UPDATE {s}: {old_by[s].get('quantity')}@{old_by[s].get('avg_price')} "
              f"-> {new_by[s]['quantity']}@{new_by[s]['avg_price']}")
    for s in removed:
        print(f"  - GONE   {s} (in holdings.csv, not in export — SOLD? verify)")
    if not (added or changed or removed):
        print("  (no changes — holdings.csv already matches the export)")

    if args.dry_run:
        print("\n--dry-run: nothing written.")
        return

    with open(HOLDINGS, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["symbol", "quantity", "avg_price"])
        w.writeheader()
        for h in sorted(new, key=lambda x: x["symbol"]):
            w.writerow(h)
    print(f"\nwrote {len(new)} holdings -> {HOLDINGS}")
    if removed:
        print("NOTE: removed names are gone from holdings.csv; if any is still a managed "
              "position, reconcile positions.csv manually.")


if __name__ == "__main__":
    main()
