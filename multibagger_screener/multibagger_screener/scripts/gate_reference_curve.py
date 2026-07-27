"""
scripts/gate_reference_curve.py — regenerate (and audit) the capital gate's
age-matched reference curve.

    python scripts/gate_reference_curve.py            # verify the frozen curve
    python scripts/gate_reference_curve.py --power    # + gate power analysis

WHY THIS EXISTS
The gate compares a live cohort against what the VALIDATED backtest reads at
the same age (CAPITAL_GATE.md §4, amended 2026-07-27). That reference lives
FROZEN in `config.GATE.expectancy_curve`, because a bar that could drift with a
re-run is not a pre-registered bar. This script is the audit trail: it recomputes
the curve from the backtest's own trades and tells you whether the frozen
numbers still reproduce. It NEVER writes config.

If it reports drift, that is not a licence to update the constant. It means
either the engine changed or the trade file changed, and CAPITAL_GATE.md §8
requires a dated re-registration with the reason written down.

METHOD (identical to journal_outcomes._plan_followed, plus a truncation)
Each entry in the canonical baseline is replayed through backtest/engine.py with
next-session-open fills, gap-aware stops, equity sizing and full costs — then
the price series is cut at entry + N days, which is exactly what the live gate
does, since live data simply ends at "today".
"""

from __future__ import annotations

import argparse
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backtest.engine import generate_signals, run_backtest
from backtest.metrics import apply_costs
from config import GATE
from data.cache import load_ohlcv

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRADES = os.path.join(ROOT, "matrix_trades", "SZ2_B_equity_cap15_r1.25.csv")
OUT = os.path.join(ROOT, "gate_reference_report.md")
_WARMUP_BARS = 400
HORIZONS = (30, 60, 90, 180, 365, None)

_SIG: dict[str, pd.DataFrame | None] = {}


def _signals_for(sym: str):
    if sym not in _SIG:
        df = load_ohlcv(sym)
        if df is None or len(df) < 60:
            _SIG[sym] = None
        else:
            try:
                _SIG[sym] = generate_signals(df.copy(), 1.0)
            except Exception:  # noqa: BLE001 — one bad series must not stop the audit
                _SIG[sym] = None
    return _SIG[sym]


def replay(sym: str, entry_date, horizon_days: int | None):
    """Blended R for one entry, measured `horizon_days` after entry."""
    sig = _signals_for(sym)
    if sig is None or sig.empty:
        return None
    hit = sig.index[sig["date"] == entry_date]
    if not len(hit):
        return None
    entry_i = int(hit[0])
    start_i = max(0, entry_i - _WARMUP_BARS)
    s = sig.iloc[start_i:].reset_index(drop=True)
    if horizon_days:
        s = s[s["date"] <= entry_date + pd.Timedelta(days=horizon_days)].reset_index(drop=True)
    entry_i -= start_i
    if entry_i >= len(s) or len(s) - entry_i < 2:
        return None
    s["breakout_today"] = False
    s.loc[entry_i, "breakout_today"] = True
    try:
        trades, _ = run_backtest({sym: s}, entry_price_col="open",
                                 stop_fill="gap_aware", size_on="equity")
    except Exception:  # noqa: BLE001
        return None
    if trades.empty:
        return None
    trades = apply_costs(trades)
    denom = float((trades["shares"] * trades["risk_per_share"]).sum())
    if denom <= 0:
        return None
    return float(trades["realized_pnl_after_costs"].sum()) / denom


def compute_curve() -> dict:
    t = pd.read_csv(TRADES, parse_dates=["entry_date"])
    entries = t.groupby(["name", "entry_date"]).size().reset_index()[["name", "entry_date"]]
    pools: dict = {h: [] for h in HORIZONS}
    for _, r in entries.iterrows():
        for h in HORIZONS:
            v = replay(r["name"], r["entry_date"], h)
            if v is not None:
                pools[h].append(v)
    return pools


def gate_power(pools: dict, trials: int = 20000, scale: float = 1.0) -> dict:
    """How often does the gate PASS a system performing exactly this well?"""
    rng = np.random.default_rng(20260727)
    out = {}
    for h, vals in pools.items():
        if len(vals) < 10:
            continue
        pool = np.array(vals) * scale
        ref = float(np.interp(min(max(h or 365, 30), 365),
                              [p[0] for p in GATE.expectancy_curve],
                              [p[1] for p in GATE.expectancy_curve]))
        bar = ref * GATE.min_expectancy_fraction
        passes = 0
        for _ in range(trials):
            s = rng.choice(pool, GATE.min_signals, replace=True)
            pos = s[s > 0]
            share = (pos.max() / pos.sum() * 100) if len(pos) else 0.0
            if (s.mean() >= bar
                    and (s <= -0.95).mean() * 100 <= GATE.max_hit_stop_pct
                    and share <= GATE.max_share_from_best_trade_pct):
                passes += 1
        out[h] = {"pool_mean": float(pool.mean()), "bar": bar,
                  "pass_pct": passes / trials * 100}
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--power", action="store_true",
                    help="also bootstrap how often the gate passes a system "
                         "performing exactly as validated")
    args = ap.parse_args()

    if not os.path.exists(TRADES):
        print(f"missing {TRADES} — matrix_trades/ is gitignored; re-run "
              f"scripts/run_sizing_matrix2.py to regenerate")
        return

    pools = compute_curve()
    frozen = dict(GATE.expectancy_curve)
    lines = ["# Gate reference curve — audit", "",
             f"Source: `{GATE.expectancy_curve_source}`", "",
             "| age | frozen in config | recomputed now | drift | n |",
             "|---|---|---|---|---|"]
    drift = []
    print(f"{'age':>8}{'frozen':>10}{'recomputed':>12}{'drift':>9}{'n':>6}")
    for h in HORIZONS:
        vals = pools.get(h) or []
        if not vals:
            continue
        got = float(np.mean(vals))
        label = f"{h}d" if h else "full"
        fz = frozen.get(h)
        d = (got - fz) if fz is not None else None
        if fz is not None and abs(d) > 0.005:
            drift.append((label, fz, got))
        print(f"{label:>8}{('%+.3f' % fz) if fz else '—':>10}{got:>+12.3f}"
              f"{('%+.3f' % d) if d is not None else '—':>9}{len(vals):>6}")
        lines.append(f"| {label} | {('%+.3f' % fz) if fz else '—'} | {got:+.3f} | "
                     f"{('%+.3f' % d) if d is not None else '—'} | {len(vals)} |")

    if drift:
        msg = ("!! CURVE DRIFT — the frozen reference no longer reproduces. "
               "Do NOT edit config to match. CAPITAL_GATE.md §8 requires a dated "
               "re-registration stating what changed (engine, trade file, or data).")
        print("\n" + msg)
        lines += ["", msg]
    else:
        print("\nfrozen curve reproduces exactly — gate reference is sound")
        lines += ["", "Frozen curve reproduces — gate reference is sound."]

    if args.power:
        lines += ["", "## Power: how often does the gate pass a system that IS working?", "",
                  "| age at judgment | pool mean R | bar | P(all conditions pass) at n=40 |",
                  "|---|---|---|---|"]
        print(f"\n{'age':>8}{'poolMean':>10}{'bar':>8}{'P(pass)':>10}")
        for h, v in gate_power(pools).items():
            label = f"{h}d" if h else "full"
            print(f"{label:>8}{v['pool_mean']:>+10.3f}{v['bar']:>+8.3f}{v['pass_pct']:>9.0f}%")
            lines.append(f"| {label} | {v['pool_mean']:+.3f} | {v['bar']:+.3f} | "
                         f"{v['pass_pct']:.0f}% |")

    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"\n-> {OUT}")


if __name__ == "__main__":
    main()
