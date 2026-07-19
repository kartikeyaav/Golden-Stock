"""
regime.py — the ONE place the market-regime sizing rule lives.

RULE (sizing matrix v3 + v3b follow-up, ADOPTED 2026-07-19): risk per trade
x0.5 whenever MARKET BREADTH — the % of the universe closing above its own
200-DMA — is below 50%. Breadth beat the previous NIFTY/150-DMA rule on the
full window (CAGR 49.5% vs 47.7%, maxDD -14.8% vs -17.6%, MAR 3.35 vs 2.70)
AND on the chop-segment guards registered in v3b (P2-segment return +13.6%
vs +9.4%, P2-segment DD -14.8% vs -17.6%). See sizing_matrix3_report.md +
sizing_matrix3b_report.md.

The nightly scan computes breadth (it already holds every chart) and
persists state/regime.json; this module READS that snapshot. If the
snapshot is missing or stale (>7 days), we fall back to the previous
adopted rule (NIFTY50 below its 150-DMA, matrix v3b 2026-07-06) — the
scale must never silently turn permissive on missing data.

Sizing only — entries are never filtered (Design Law / brief section 2B).

Previously duplicated in daily_scan.py and run_shortlist.py — centralized in
the 2026-07-07 audit so the rule can't drift between paths.
"""

from __future__ import annotations

import json
import os
from datetime import datetime

from data.cache import load_ohlcv

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGIME_SNAPSHOT = os.path.join(ROOT, "state", "regime.json")

BREADTH_HALF_BELOW_PCT = 50.0
SNAPSHOT_MAX_AGE_DAYS = 7


def save_breadth_snapshot(above: int, total: int) -> dict:
    """Called by the nightly scan after tagging (it already loaded every
    chart — breadth costs nothing extra there)."""
    pct = round(above / total * 100, 1) if total else None
    payload = {"date": datetime.now().strftime("%Y-%m-%d"),
               "breadth_pct_above_200dma": pct,
               "above": above, "total": total}
    os.makedirs(os.path.dirname(REGIME_SNAPSHOT), exist_ok=True)
    with open(REGIME_SNAPSHOT, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=1)
    return payload


def _breadth_scale() -> float | None:
    try:
        with open(REGIME_SNAPSHOT, encoding="utf-8") as f:
            snap = json.load(f)
        age = (datetime.now() - datetime.strptime(snap["date"], "%Y-%m-%d")).days
        pct = snap.get("breadth_pct_above_200dma")
        if age <= SNAPSHOT_MAX_AGE_DAYS and pct is not None and snap.get("total", 0) >= 100:
            return 0.5 if float(pct) < BREADTH_HALF_BELOW_PCT else 1.0
    except (OSError, ValueError, KeyError):
        pass
    return None


def market_risk_scale() -> float:
    scale = _breadth_scale()
    if scale is not None:
        return scale
    # fallback: the previously adopted NIFTY/150-DMA rule (matrix v3b)
    bench = load_ohlcv("NIFTY50")
    if bench is None or len(bench) < 150:
        return 1.0
    sma150 = bench["close"].rolling(150).mean().iloc[-1]
    return 0.5 if float(bench["close"].iloc[-1]) < float(sma150) else 1.0


def regime_description() -> str:
    """One line for AI briefings / cards — names the rule actually in force."""
    scale = _breadth_scale()
    if scale is not None:
        try:
            snap = json.load(open(REGIME_SNAPSHOT, encoding="utf-8"))
            pct = snap.get("breadth_pct_above_200dma")
            state = "DEFENSIVE (half size)" if scale < 1.0 else "NORMAL (full size)"
            return (f"Market regime: {state} — {pct}% of the universe above its "
                    f"200-DMA (breadth rule, half risk below {BREADTH_HALF_BELOW_PCT:.0f}%)")
        except (OSError, ValueError):
            pass
    s = market_risk_scale()
    return ("Market regime: DEFENSIVE (half size) — NIFTY below its 150-DMA (fallback rule)"
            if s < 1.0 else
            "Market regime: NORMAL (full size) — NIFTY above its 150-DMA (fallback rule)")
