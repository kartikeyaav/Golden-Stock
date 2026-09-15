"""test_benchmarks_are_not_stocks.py - a benchmark series is priced every night
and never tagged, triggered, ranked or counted in breadth like a stock.

WHY (2026-09-15). The scan's tagging loop skipped a hard-coded "NIFTY50" while
the price refresh watched every entry in update_prices.BENCHMARK_SYMBOLS.
MOMENTUM100 (the capital gate's comparator ETF) joined that list on 07-26 and
was tagged nightly from then on: it surfaced as a blank screener row, sat in
the breadth count that sizes plans and in the RS ranking, and carried an armed
entry trigger. It never fired. These tests keep the skip derived from the list.

Run:  python -m pytest tests/test_benchmarks_are_not_stocks.py -q
"""

from __future__ import annotations

import os
import sys

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))


def test_every_benchmark_is_priced_but_none_is_scanned_as_a_stock():
    import daily_scan
    from update_prices import BENCHMARK_SYMBOLS, universe_and_holdings_symbols
    from config import GATE

    watched = universe_and_holdings_symbols(ROOT)
    for b in BENCHMARK_SYMBOLS:
        assert b in watched, f"{b} is no longer priced - the gate would read a stale comparator"
    assert GATE.benchmark_symbol in BENCHMARK_SYMBOLS

    scanned = daily_scan.setup_symbols(watched)
    leaked = [b for b in BENCHMARK_SYMBOLS if b in scanned]
    assert not leaked, f"benchmark series scanned as stocks: {leaked}"

    universe = pd.read_csv(os.path.join(ROOT, "universe.csv"))["symbol"].tolist()
    lost = [s for s in universe if s not in scanned]
    assert not lost, f"real universe names dropped from the scan: {lost[:10]}"


def test_a_new_benchmark_is_skipped_without_a_code_change():
    import daily_scan
    saved = list(daily_scan.BENCHMARK_SYMBOLS)
    try:
        daily_scan.BENCHMARK_SYMBOLS.append("SOMEFUTUREINDEX")
        out = daily_scan.setup_symbols(["AAA", "SOMEFUTUREINDEX", "NIFTY50", "BBB"])
        assert out == ["AAA", "BBB"], out
    finally:
        daily_scan.BENCHMARK_SYMBOLS[:] = saved


def test_the_tagging_loop_uses_the_derived_set():
    src = open(os.path.join(ROOT, "scripts", "daily_scan.py"), encoding="utf-8").read()
    assert "for sym in setup_symbols(symbols):" in src, \
        "the tagging loop no longer filters benchmark series"
    assert 'if sym == "NIFTY50":' not in src, "the hard-coded single-benchmark skip is back"


if __name__ == "__main__":
    failures = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"ok   {name}")
            except Exception as e:  # noqa: BLE001
                failures += 1
                print(f"FAIL {name}: {type(e).__name__}: {str(e)[:200]}")
    print(f"\n{failures} failure(s)")
    sys.exit(1 if failures else 0)
