"""
scripts/run_a2_matrix.py — PREREG_2026-07-30 config A2: the IPO-base entry
class for names too young for the 8-point trend template.

The template needs ~260 bars (200-DMA + a 20-day lookback on it + a 52-week
range), so a recent listing can NEVER qualify and its only path is the EPISODIC
PIVOT class. Measured blind spot: IREDA, WAAREERTL. Young names are ~2x
over-represented among top movers (scoping table in the pre-registration).

NOTE ON MIN_ROWS. Every prior matrix skipped symbols with fewer than 300 rows,
which silently excluded the whole population this test is about — the exclusion
was in the harness, not just the strategy. A2 lowers the floor to 80 and marks
IPO entries ONLY while a name is still under 260 bars, so the two classes never
overlap: below 260 the IPO base can fire, at and above it the normal template
takes over exactly as today.

Configs (fixed in the pre-registration, committed 130d1b4 before this ran):

  A2_control  canonical baseline, young names excluded as today
  A2_a        IPO base, min 60 bars, 10-week window, breakout >=1.5x vol  [PRIMARY]
  A2_b        as A2_a with min 90 bars
  A2_c        as A2_a but requiring the EP volume standard, >=3x

Decision rule — A2_a must satisfy ALL THREE: standalone expectancy >= +0.75R
(EP cleared +1.38R), P2 cohort >= 0, combined MAR >= 3.58 with max DD no worse
than -20.7%. Plus a sample floor fixed before the entry count was known: fewer
than 25 IPO entries across the window = MEASURED BUT NOT ADOPTED.

    python scripts/run_a2_matrix.py
"""

from __future__ import annotations

import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backtest.engine import generate_ipo_signals, generate_signals, run_backtest
from data.cache import list_cached, load_ohlcv
from scoring.pit_fundamentals import PITFundamentals
from run_matrix3 import P1_END, STARTING_CASH, WINDOW_START, cohorts
from run_a1_matrix import summarize

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MIN_ROWS = 80          # deliberately far below the usual 300 — see module docstring
TEMPLATE_BARS = 260    # above this the normal template applies; below it, IPO base
IPO_COL = "ipo_today"
BAR_MAR, BAR_DD, BAR_EXP, MIN_ENTRIES = 3.58, -20.7, 0.75, 25


def main() -> None:
    universe = pd.read_csv(os.path.join(ROOT, "universe.csv"))
    industry_by_sym = dict(zip(universe["symbol"], universe["industry"]))
    cached = set(list_cached())
    bench = load_ohlcv("NIFTY50")

    signals, ipo = {}, {"a": {}, "b": {}, "c": {}}
    young_names = 0
    t0 = time.time()
    for i, sym in enumerate(universe["symbol"], 1):
        if sym not in cached:
            continue
        df = load_ohlcv(sym)
        if df is None or len(df) < MIN_ROWS:
            continue
        pit = PITFundamentals(sym, industry_by_sym.get(sym))
        series = pit.daily_score_series(df)
        sig = generate_signals(df, series if not series.empty else np.nan)
        sig.loc[sig["date"] < WINDOW_START, "breakout_today"] = False
        signals[sym] = sig

        bar_no = pd.Series(range(len(sig)), index=sig.index)
        # a name is only "young" for its first TEMPLATE_BARS bars; the window
        # filter keeps the comparison identical to every other matrix
        young = (bar_no < TEMPLATE_BARS) & (sig["date"] >= WINDOW_START)
        if young.any():
            young_names += 1
        for key, kw in (("a", dict(min_bars=60)),
                        ("b", dict(min_bars=90)),
                        ("c", dict(min_bars=60, vol_multiple=3.0))):
            s = generate_ipo_signals(df, series if not series.empty else np.nan, **kw)
            ipo[key][sym] = (s["breakout_today"] & young).to_numpy()
        if i % 100 == 0:
            print(f"  signals {i}/{len(universe)} ({time.time()-t0:.0f}s)", flush=True)
    print(f"signals ready: {len(signals)} symbols, {young_names} with a young "
          f"period in-window, {(time.time()-t0)/60:.1f} min", flush=True)
    for k in "abc":
        print(f"  IPO triggers ({k}): {int(sum(m.sum() for m in ipo[k].values()))}",
              flush=True)

    b = bench.copy()
    b["sma150"] = b["close"].rolling(150).mean()
    regime = pd.Series(np.where(b["close"] < b["sma150"], 0.5, 1.0),
                       index=pd.to_datetime(b["date"]))

    results = []

    def run(name, masks=None):
        sigs = signals
        kw = {}
        if masks is not None:
            sigs = {}
            for sym, d in signals.items():
                x = d.copy()
                x[IPO_COL] = masks[sym]
                sigs[sym] = x
            kw = dict(anticipation_col=IPO_COL, anticipation_class_name="ipo",
                      anticipation_priority=False,   # an IPO base IS a breakout
                      anticipation_risk_mult=1.0, anticipation_max_slots=None)
        trades, equity = run_backtest(sigs, min_fundamental_score=0.0,
                                      starting_cash=STARTING_CASH,
                                      size_on="equity", risk_scale=regime, **kw)
        if trades.empty:
            print(f"[{name}] NO TRADES"); return
        r = summarize(name, trades, equity)
        results.append(r)
        cls = " · ".join(f"{c}:{v['positions']}@{v['expectancy_r']}R"
                         for c, v in sorted(r["by_class"].items()))
        print(f"[{name}] pos={r['positions']} exp={r['blended'].get('expectancy_r')}R "
              f"P2={r['cohorts']['P2'].get('expectancy_r')} "
              f"cagr={r['equity'].get('cagr_pct')}% dd={r['equity'].get('max_drawdown_pct')}% "
              f"MAR={r['mar']} | {cls}", flush=True)

    run("A2_control")
    run("A2_a", ipo["a"])
    run("A2_b", ipo["b"])
    run("A2_c", ipo["c"])

    by = {r["config"]: r for r in results}
    lines = ["# A2 — IPO-base entry class for names under the template's 260 bars", "",
             "Pre-registration: PREREG_2026-07-30.md (committed before this ran).",
             f"Bars: standalone expectancy >= +{BAR_EXP}R · P2 >= 0 · combined "
             f"MAR >= {BAR_MAR} · maxDD no worse than {BAR_DD}% · >= {MIN_ENTRIES} entries.",
             "", f"Symbols with a young period in-window: {young_names}", "",
             "| config | pos | exp | P2 | CAGR | maxDD | MAR | IPO class |",
             "|---|--:|--:|--:|--:|--:|--:|---|"]
    for r in results:
        ipo_cls = r["by_class"].get("ipo", {})
        lines.append(f"| {r['config']} | {r['positions']} | "
                     f"{r['blended'].get('expectancy_r')}R | "
                     f"{r['cohorts']['P2'].get('expectancy_r')} | "
                     f"{r['equity'].get('cagr_pct')}% | "
                     f"{r['equity'].get('max_drawdown_pct')}% | {r['mar']} | "
                     f"{ipo_cls.get('positions', 0)} entries @ "
                     f"{ipo_cls.get('expectancy_r', '—')}R |")

    a = by.get("A2_a")
    if a:
        ic = a["by_class"].get("ipo", {})
        n = ic.get("positions", 0)
        exp = ic.get("expectancy_r") or -99
        checks = {
            f">= {MIN_ENTRIES} IPO entries": n >= MIN_ENTRIES,
            f"standalone exp >= +{BAR_EXP}R": exp >= BAR_EXP,
            "P2 >= 0": (a["cohorts"]["P2"].get("expectancy_r") or -1) >= 0,
            f"MAR >= {BAR_MAR}": (a["mar"] or 0) >= BAR_MAR,
            f"maxDD >= {BAR_DD}%": (a["equity"].get("max_drawdown_pct") or -99) >= BAR_DD,
        }
        lines += ["", "## Verdict (A2_a, the pre-registered primary)", ""]
        for k, v in checks.items():
            lines.append(f"- {'PASS' if v else 'FAIL'} — {k}")
        if n < MIN_ENTRIES:
            verdict = "MEASURED BUT NOT ADOPTED (sample floor)"
        else:
            verdict = "ADOPTED" if all(checks.values()) else "REJECTED"
        lines += ["", f"**{verdict}**", ""]
    out = os.path.join(ROOT, "a2_matrix_report.md")
    open(out, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print("\n".join(lines[-12:]))
    print(f"\n-> {out}")


if __name__ == "__main__":
    main()
