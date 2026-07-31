"""
scripts/run_a1_matrix.py — PREREG_2026-07-30 config A1: does a fundamentally
filtered ANTICIPATION sleeve add anything at the PORTFOLIO level?

V3a already measured this entry class in isolation (+0.41R, positive both
cohorts, vs +0.06R price-only) by overwriting breakout_today — so it ran a
portfolio of anticipation entries and nothing else. That design cannot answer
the question that actually decides adoption: when anticipation entries sit
BESIDE breakouts in one book, do they add return or do they consume slots a
+1.67R breakout would have taken to fund a +0.41R one?

Configs (fixed in the pre-registration, committed 130d1b4 before this ran):

  A1_control  canonical baseline, no sleeve                (reproduction check)
  A1_a        sleeve, fundamentals >=0.60, risk x0.5, 4 OWN slots   [PRIMARY]
  A1_b        same but SHARING the 12 breakout slots       (cannibalisation probe)
  A1_c        sleeve at full risk x1.0, 4 own slots        (dose-response)
  A1_d        sleeve, fundamentals >=0.70, risk x0.5       (dose-response)

Decision rule — A1_a must satisfy ALL FOUR: combined MAR >= 3.58, max DD no
worse than -20.7%, P2 cohort >= 0, combined CAGR >= baseline. Non-monotonic
dose-response across (a,c) or (a,d) rejects A1 regardless of what A1_a shows.

The anticipation mask is IMPORTED from run_matrix3 rather than reimplemented,
so this test and the V3a result it builds on cannot drift apart.

    python scripts/run_a1_matrix.py
"""

from __future__ import annotations

import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backtest.engine import generate_signals, run_backtest
from backtest.metrics import apply_costs, equity_stats, lot_breakdown, trade_stats
from data.cache import list_cached, load_ohlcv
from scoring.pit_fundamentals import PITFundamentals
from run_matrix3 import (P1_END, STARTING_CASH, WINDOW_START, anticipation_mask,
                         cohorts)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRADES_DIR = os.path.join(ROOT, "matrix_trades")
MIN_ROWS = 300
ANTI_COL = "anticipation_today"

# pre-registered comparators
BAR_MAR, BAR_DD = 3.58, -20.7


def summarize(name, trades, equity):
    trades = apply_costs(trades)
    os.makedirs(TRADES_DIR, exist_ok=True)
    trades.to_csv(os.path.join(TRADES_DIR, f"{name}.csv"), index=False)
    eq = equity_stats(equity[equity["date"] >= WINDOW_START], STARTING_CASH)
    cagr, dd = eq.get("cagr_pct"), eq.get("max_drawdown_pct")
    mar = round(cagr / abs(dd), 2) if cagr and dd else None
    by_class = {}
    if "entry_class" in trades.columns:
        for cls, g in trades.groupby("entry_class"):
            s = trade_stats(g, pnl_col="realized_pnl_after_costs",
                            r_col="r_multiple_after_costs")
            by_class[cls] = {"positions": g[["name", "entry_date"]].drop_duplicates().shape[0],
                             "expectancy_r": s.get("expectancy_r")}
    return {
        "config": name,
        "positions": trades[["name", "entry_date"]].drop_duplicates().shape[0],
        "blended": trade_stats(trades, pnl_col="realized_pnl_after_costs",
                               r_col="r_multiple_after_costs"),
        "core": lot_breakdown(trades, pnl_col="realized_pnl_after_costs",
                              r_col="r_multiple_after_costs").get("core", {}),
        "cohorts": cohorts(trades), "equity": eq, "mar": mar, "by_class": by_class,
    }


def main() -> None:
    universe = pd.read_csv(os.path.join(ROOT, "universe.csv"))
    industry_by_sym = dict(zip(universe["symbol"], universe["industry"]))
    cached = set(list_cached())
    bench = load_ohlcv("NIFTY50")

    signals, masks60, masks70 = {}, {}, {}
    t0 = time.time()
    for i, sym in enumerate(universe["symbol"], 1):
        if sym not in cached:
            continue
        df = load_ohlcv(sym)
        if df is None or len(df) < MIN_ROWS:
            continue
        pit = PITFundamentals(sym, industry_by_sym.get(sym))
        series = pit.daily_score_series(df)
        s = series if not series.empty else None
        sig = generate_signals(df, series if not series.empty else np.nan)
        sig.loc[sig["date"] < WINDOW_START, "breakout_today"] = False
        signals[sym] = sig
        in_win = sig["date"] >= WINDOW_START
        masks60[sym] = (anticipation_mask(df, bench, s, 0.60) & in_win).to_numpy()
        masks70[sym] = (anticipation_mask(df, bench, s, 0.70) & in_win).to_numpy()
        if i % 100 == 0:
            print(f"  signals {i}/{len(universe)} ({time.time()-t0:.0f}s)", flush=True)
    print(f"signals ready: {len(signals)} in {(time.time()-t0)/60:.1f} min", flush=True)

    b = bench.copy()
    b["sma150"] = b["close"].rolling(150).mean()
    regime = pd.Series(np.where(b["close"] < b["sma150"], 0.5, 1.0),
                       index=pd.to_datetime(b["date"]))

    def with_mask(masks):
        out = {}
        for sym, df in signals.items():
            d = df.copy()
            d[ANTI_COL] = masks[sym]
            out[sym] = d
        return out

    sig60, sig70 = with_mask(masks60), with_mask(masks70)
    n60 = int(sum(m.sum() for m in masks60.values()))
    n70 = int(sum(m.sum() for m in masks70.values()))
    print(f"anticipation triggers in window: >=0.60 -> {n60} · >=0.70 -> {n70}",
          flush=True)

    results = []

    def run(name, sigs, **kw):
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
              f"P1={r['cohorts']['P1'].get('expectancy_r')} "
              f"P2={r['cohorts']['P2'].get('expectancy_r')} "
              f"cagr={r['equity'].get('cagr_pct')}% dd={r['equity'].get('max_drawdown_pct')}% "
              f"MAR={r['mar']} | {cls}", flush=True)

    run("A1_control", signals)
    run("A1_a", sig60, anticipation_col=ANTI_COL,
        anticipation_risk_mult=0.5, anticipation_max_slots=4)
    run("A1_b", sig60, anticipation_col=ANTI_COL,
        anticipation_risk_mult=0.5, anticipation_max_slots=None)
    run("A1_c", sig60, anticipation_col=ANTI_COL,
        anticipation_risk_mult=1.0, anticipation_max_slots=4)
    run("A1_d", sig70, anticipation_col=ANTI_COL,
        anticipation_risk_mult=0.5, anticipation_max_slots=4)

    # ---- verdict against the pre-registered rule -----------------------------
    by = {r["config"]: r for r in results}
    lines = ["# A1 — anticipation sleeve at portfolio level", "",
             f"Pre-registration: PREREG_2026-07-30.md (committed before this ran).",
             f"Bars: combined MAR >= {BAR_MAR} · max DD no worse than {BAR_DD}% · "
             f"P2 >= 0 · CAGR >= baseline.", "",
             f"Anticipation triggers in window: >=0.60 -> {n60}, >=0.70 -> {n70}", "",
             "| config | pos | exp | P1 | P2 | CAGR | maxDD | MAR |",
             "|---|--:|--:|--:|--:|--:|--:|--:|"]
    for r in results:
        lines.append(f"| {r['config']} | {r['positions']} | "
                     f"{r['blended'].get('expectancy_r')}R | "
                     f"{r['cohorts']['P1'].get('expectancy_r')} | "
                     f"{r['cohorts']['P2'].get('expectancy_r')} | "
                     f"{r['equity'].get('cagr_pct')}% | "
                     f"{r['equity'].get('max_drawdown_pct')}% | {r['mar']} |")

    a, ctl = by.get("A1_a"), by.get("A1_control")
    if a and ctl:
        checks = {
            f"MAR >= {BAR_MAR}": (a["mar"] or 0) >= BAR_MAR,
            f"maxDD >= {BAR_DD}%": (a["equity"].get("max_drawdown_pct") or -99) >= BAR_DD,
            "P2 >= 0": (a["cohorts"]["P2"].get("expectancy_r") or -1) >= 0,
            "CAGR >= baseline": ((a["equity"].get("cagr_pct") or 0)
                                 >= (ctl["equity"].get("cagr_pct") or 0)),
        }
        # DOSE-RESPONSE (corrected 2026-07-31). The original clause only fired
        # when BOTH probes beat the primary, which cannot detect the failure
        # that actually occurred: doubling sleeve risk COLLAPSED MAR 2.76 -> 1.89
        # and breached the DD bar. A real effect degrades gracefully under a
        # bigger dose; one that inverts is fragile. Fail if either probe moves
        # the metric by more than a third, in either direction.
        mono = True
        for probe in ("A1_c", "A1_d"):
            if by.get(probe) and a["mar"]:
                rel = abs((by[probe]["mar"] or 0) - a["mar"]) / a["mar"]
                if rel > 0.33:
                    mono = False
        # The pre-registered 3.58 came from the breakout+EP figure while this
        # harness runs breakouts only, so it is unreachable here by construction
        # (see the OUTCOME block in PREREG_2026-07-30.md). Report BOTH readings;
        # never silently substitute the reachable one for the registered one.
        ctl_mar = ctl["mar"] or 0
        lines += ["", f"> Bar note: the registered MAR bar ({BAR_MAR}) was taken from "
                      f"the breakout+EP configuration; this harness is breakout-only "
                      f"and its control reproduces at MAR {ctl_mar}. Both readings "
                      f"are shown. The bar was not lowered after the fact.", ""]
        checks[f"MAR >= control ({ctl_mar})"] = (a["mar"] or 0) >= ctl_mar
        checks["P2 >= control (no chop degradation)"] = (
            (a["cohorts"]["P2"].get("expectancy_r") or -1)
            >= (ctl["cohorts"]["P2"].get("expectancy_r") or 0))
        lines += ["", "## Verdict (A1_a, the pre-registered primary)", ""]
        for k, v in checks.items():
            lines.append(f"- {'PASS' if v else 'FAIL'} — {k}")
        lines.append(f"- {'PASS' if mono else 'FAIL'} — dose-response coherent")
        verdict = "ADOPTED" if all(checks.values()) and mono else "REJECTED"
        lines += ["", f"**{verdict}**", ""]
        if by.get("A1_b") and a:
            lines.append(f"Cannibalisation probe: A1_b MAR {by['A1_b']['mar']} vs "
                         f"A1_a {a['mar']} — "
                         f"{'sharing slots is worse, as predicted' if (by['A1_b']['mar'] or 0) < (a['mar'] or 0) else 'sharing slots is NOT worse'}.")
    out = os.path.join(ROOT, "a1_matrix_report.md")
    open(out, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print("\n".join(lines[-14:]))
    print(f"\n-> {out}")


if __name__ == "__main__":
    main()
