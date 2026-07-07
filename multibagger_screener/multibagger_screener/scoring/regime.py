"""
regime.py — the ONE place the market-regime sizing rule lives (matrix v3b,
ADOPTED 2026-07-06: identical trades, higher CAGR, lower drawdown).

Rule: risk per trade x0.5 whenever NIFTY50 closes below its 150-DMA.
Sizing only — entries are never filtered (Design Law / brief section 2B).

Previously duplicated in daily_scan.py and run_shortlist.py — centralized in
the 2026-07-07 audit so the rule can't drift between paths.
"""

from __future__ import annotations

from data.cache import load_ohlcv


def market_risk_scale() -> float:
    bench = load_ohlcv("NIFTY50")
    if bench is None or len(bench) < 150:
        return 1.0
    sma150 = bench["close"].rolling(150).mean().iloc[-1]
    return 0.5 if float(bench["close"].iloc[-1]) < float(sma150) else 1.0
