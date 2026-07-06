"""
scripts/sync_positions.py — reconcile positions.csv (the plans the system
manages) against holdings.csv (what you actually hold). Catches the classic
failure: you executed a sale but the tracker still watches a ghost, or you
bought something the system isn't protecting.

holdings.csv is the ground truth you refresh (manually, or in a Claude
session via the Zerodha connection: "sync my holdings").

    python scripts/sync_positions.py
"""

from __future__ import annotations

import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def check() -> list[str]:
    problems = []
    hp = os.path.join(ROOT, "holdings.csv")
    pp = os.path.join(ROOT, "positions.csv")
    holdings = pd.read_csv(hp) if os.path.exists(hp) else pd.DataFrame(columns=["symbol", "quantity"])
    positions = pd.read_csv(pp) if os.path.exists(pp) else pd.DataFrame()

    held = dict(zip(holdings.get("symbol", []), holdings.get("quantity", [])))

    for _, p in positions.iterrows():
        sym = p["symbol"]
        open_sh = 0
        if str(p.get("trading_open", "")).lower() in ("true", "1"):
            open_sh += int(p["shares_trading"])
        if str(p.get("core_open", "")).lower() in ("true", "1"):
            open_sh += int(p["shares_core"])
        if open_sh == 0:
            continue
        actual = int(held.get(sym, 0))
        if actual == 0:
            problems.append(f"{sym}: positions.csv tracks {open_sh} open shares but "
                            "holdings show NONE — did you exit? Close the lots in positions.csv")
        elif actual < open_sh:
            problems.append(f"{sym}: tracking {open_sh} open shares but holdings show "
                            f"only {actual} — partial exit not recorded?")

    tracked = set(positions.get("symbol", []))
    for sym, qty in held.items():
        if sym not in tracked and qty > 0:
            problems.append(f"{sym}: {qty} shares held but NOT under position management — "
                            "no stop is being watched for this")
    return problems


def main() -> None:
    problems = check()
    if not problems:
        print("positions and holdings are in sync")
    else:
        print(f"{len(problems)} mismatch(es):")
        for p in problems:
            print(f"  !! {p}")


if __name__ == "__main__":
    main()
