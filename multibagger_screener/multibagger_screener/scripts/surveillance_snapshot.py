"""
scripts/surveillance_snapshot.py — exchange surveillance state for the MAIN
universe. Writes `state/surveillance.json`. Display only, never a gate.

    python scripts/surveillance_snapshot.py            # refresh the snapshot
    python scripts/surveillance_snapshot.py --check    # print, write nothing

WHY THIS EXISTS. The penny screen gates hard on ASM / GSM / circuit band /
settlement series, on the argument that in that class *you lose because you
cannot get out*. That argument does not stop at ₹100 a share. Indian
small- and mid-caps enter ASM regularly — a 20% band becomes 5%, intraday
leverage goes to zero, 100% margin applies, and the name can no longer be
pledged as collateral. A 2.5×ATR stop on a stock that just moved to a 5%
band is a stop that cannot fill. The main system has been structurally blind
to all of it while its own penny screen treated it as the single most
important fact about a stock.

The data was already being fetched nightly for the penny universe
(`data/nse_all.py`). This file points it at the other 651 names.

NOT A GATE — deliberately. The evidence lock (PROJECT_BRIEF §2B) says entries
are technical-only and change only on pre-registered evidence, and no matrix
has ever tested a surveillance filter. So this writes a FLAG that renders on
the card, the Actionable row and the drawer, and changes nothing about what
fires, what is scored or how anything is sized. If it should ever gate, that
needs its own registered run — the same rule that rejected the other overlays.

Non-fatal by construction: NSE occasionally blocks datacenter IPs, so a
failure leaves the previous snapshot in place, marks it stale and lets the
scan continue. A missing snapshot means "unknown", never "clean".
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.nse_all import asm_symbols, bands_and_gsm, symbol_master

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "state", "surveillance.json")

# a band at or below this is the "cannot exit" case the penny screen refuses:
# a 2.5xATR stop needs more room than the day's whole permitted range
TIGHT_BAND_PCT = 10.0
# settlement series that are not normal rolling settlement. BE/BZ are
# trade-to-trade: compulsory delivery, no intraday, and usually a surveillance
# signal in themselves.
ABNORMAL_SERIES = ("BE", "BZ", "SM", "ST", "IL")


def universe_symbols() -> list[str]:
    syms: list[str] = []
    for name in ("universe.csv", "holdings.csv"):
        p = os.path.join(ROOT, name)
        if os.path.exists(p):
            try:
                syms += pd.read_csv(p)["symbol"].astype(str).tolist()
            except (ValueError, KeyError, OSError):
                pass
    return list(dict.fromkeys(syms))


def build(symbols: list[str] | None = None) -> dict:
    symbols = symbols or universe_symbols()
    want = set(symbols)

    bands = bands_and_gsm()
    asm = asm_symbols()
    master = symbol_master()

    band_by = {}
    gsm_by = {}
    for _, r in bands.iterrows():
        s = str(r["symbol"])
        if s not in want:
            continue
        # a symbol can appear on several series rows; keep the tightest band
        b = r["band_pct"]
        if pd.notna(b):
            prev = band_by.get(s)
            band_by[s] = float(b) if prev is None else min(prev, float(b))
        if bool(r.get("in_gsm")):
            gsm_by[s] = str(r.get("gsm_stage") or "yes")

    series_by = {}
    for _, r in master.iterrows():
        s = str(r["symbol"])
        if s in want:
            series_by[s] = str(r["series"])

    out: dict[str, dict] = {}
    for s in symbols:
        flags, band = [], band_by.get(s)
        if s in asm:
            flags.append({"code": "ASM", "detail": asm[s],
                          "why": ("exchange flag for manipulation or abnormal "
                                  "volatility. 100% margin, no intraday leverage.")})
        if s in gsm_by:
            flags.append({"code": "GSM", "detail": f"stage {gsm_by[s]}",
                          "why": ("price far out of line with fundamentals. "
                                  "Trading restricted, can become call-auction only.")})
        if band is not None and band <= TIGHT_BAND_PCT:
            flags.append({"code": f"BAND {band:g}%", "detail": f"{band:g}% circuit band",
                          "why": ("the day's range is narrower than a normal ATR "
                                  "stop, so a gap to the limit fills no stop at all.")})
        ser = series_by.get(s)
        if ser and ser in ABNORMAL_SERIES:
            flags.append({"code": ser, "detail": f"{ser} settlement series",
                          "why": ("trade-to-trade or SME settlement: compulsory "
                                  "delivery, no intraday exit.")})
        if flags:
            out[s] = {"flags": flags, "band": band, "series": ser,
                      "worst": flags[0]["code"]}

    return {
        "generated": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "n_checked": len(symbols),
        "n_flagged": len(out),
        "asm_total": len(asm),
        "syms": out,
        "note": ("Display only. Surveillance has never been tested as an entry "
                 "filter here, so it flags and does not gate."),
    }


def load() -> dict:
    """Read the snapshot. Missing/unreadable = unknown, never 'clean'."""
    if not os.path.exists(OUT):
        return {}
    try:
        return json.load(open(OUT, encoding="utf-8"))
    except (ValueError, OSError):
        return {}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="print, write nothing")
    args = ap.parse_args()
    snap = build()
    top = sorted(snap["syms"].items(), key=lambda kv: kv[0])[:15]
    print(f"surveillance: {snap['n_flagged']} of {snap['n_checked']} watched names "
          f"carry a flag ({snap['asm_total']} symbols on ASM market-wide)")
    for s, d in top:
        print(f"  {s:14s} {', '.join(f['code'] for f in d['flags'])}")
    if len(snap["syms"]) > 15:
        print(f"  ... {len(snap['syms']) - 15} more")
    if args.check:
        return
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(snap, f, indent=1)
    print(f"-> {OUT}")


if __name__ == "__main__":
    main()
