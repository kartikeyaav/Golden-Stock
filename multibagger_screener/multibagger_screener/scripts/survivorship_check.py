"""
scripts/survivorship_check.py — put a NUMBER on the survivorship caveat.

Fetches archived index constituent lists (Wayback Machine snapshots nearest
the backtest window start, 2023-08) and compares against today's universe:
names that were constituents THEN but are invisible to our backtest NOW are
exactly the potential losers the backtest never saw.

    python scripts/survivorship_check.py
"""

from __future__ import annotations

import io
import json
import os
import sys
import urllib.parse
import urllib.request

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.cache import list_cached

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
TARGET_TS = "20230801"

# non-www variant — the one the Wayback Machine actually crawled; nearest
# snapshots are ~2024-07 (mid-window), so this measures churn over the BACK
# HALF of the window — reported honestly in the output.
SOURCES = {
    "smallcap250": "https://niftyindices.com/IndexConstituent/ind_niftysmallcap250list.csv",
    "midcap150": "https://niftyindices.com/IndexConstituent/ind_niftymidcap150list.csv",
    "microcap250": "https://niftyindices.com/IndexConstituent/ind_niftymicrocap250_list.csv",
}


def wayback_snapshot(url: str, ts: str) -> tuple[str, str] | None:
    api = ("http://archive.org/wayback/available?url="
           + urllib.parse.quote(url, safe="") + f"&timestamp={ts}")
    req = urllib.request.Request(api, headers=_UA)
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode())
    snap = data.get("archived_snapshots", {}).get("closest")
    if not snap or not snap.get("available"):
        return None
    return snap["url"], snap.get("timestamp", "")


def fetch_csv(url: str) -> pd.DataFrame:
    req = urllib.request.Request(url, headers=_UA)
    with urllib.request.urlopen(req, timeout=60) as resp:
        raw = resp.read().decode("utf-8-sig", "ignore")
    return pd.read_csv(io.StringIO(raw))


def main() -> None:
    today = set(pd.read_csv(os.path.join(ROOT, "universe.csv"))["symbol"])
    cached = set(list_cached())

    then_symbols: set[str] = set()
    snap_dates = []
    for name, url in SOURCES.items():
        snap = wayback_snapshot(url, TARGET_TS)
        if snap is None:
            print(f"[{name}] no snapshot found near {TARGET_TS}")
            continue
        snap_url, ts = snap
        try:
            df = fetch_csv(snap_url)
        except Exception as e:  # noqa: BLE001
            print(f"[{name}] snapshot fetch failed: {str(e)[:80]}")
            continue
        df.columns = [c.strip().lower() for c in df.columns]
        sym_col = next((c for c in df.columns if "symbol" in c), None)
        if sym_col is None:
            print(f"[{name}] no symbol column in snapshot")
            continue
        syms = set(df[sym_col].astype(str).str.strip())
        then_symbols |= syms
        snap_dates.append(f"{name}: {ts[:8]} ({len(syms)} names)")
        print(f"[{name}] snapshot {ts[:8]}: {len(syms)} constituents")

    if not then_symbols:
        print("No snapshots retrievable — survivorship stays an unquantified caveat.")
        return

    vanished = then_symbols - today
    vanished_and_unpriced = vanished - cached
    still_here = then_symbols & today

    lines = [
        "# Survivorship check — 2023-08 constituents vs today",
        "",
        f"- Snapshots: {'; '.join(snap_dates)}",
        f"- 2023-08 constituents found: {len(then_symbols)}",
        f"- Still in today's universe: {len(still_here)} "
        f"({len(still_here)/len(then_symbols)*100:.1f}%)",
        f"- Left the universe since: {len(vanished)} "
        f"({len(vanished)/len(then_symbols)*100:.1f}%)",
        f"- Of those, invisible to our backtest (no price cache): "
        f"{len(vanished_and_unpriced)}",
        "",
        "Interpretation: names that left include promotions to larger indices",
        "(harmless upward drift), true deletions, and delistings. The",
        f"{len(vanished)/len(then_symbols)*100:.0f}% churn bounds how much of the 2023-08 opportunity set",
        "the backtest may be missing; treat backtest expectancy as optimistic",
        "by up to roughly this order. (Design Law #4: directional only.)",
        "",
        f"Departed symbols: {', '.join(sorted(vanished)) if vanished else 'none'}",
    ]
    out = os.path.join(ROOT, "survivorship_report.md")
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("\n".join(lines[:10]))
    print(f"\n-> {out}")


if __name__ == "__main__":
    main()
