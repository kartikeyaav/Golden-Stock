"""
scripts/journal_outcomes.py — fill in what happened AFTER each journaled
signal (the forward-validation scorecard). Reads journal/signals_journal.csv,
writes journal/journal_outcomes.csv (regenerated each run — the journal
itself is never touched). Run weekly, or whenever curious:

    python scripts/journal_outcomes.py

TWO RULERS, both reported, because they measure different things
(AUDIT_2026-07-25 Findings 2 and 3):

  RAW (the original columns — return_to_date_pct, max_favorable_R,
  max_adverse_R, hit_suggested_stop, r_to_date, status)
      Marks the signal to market from the alert-night CLOSE and books a
      stop-out at exactly -1.0R. Kept for continuity with every earlier
      reading of this file. It is NOT comparable to the backtest: it never
      applies the two-lot exits, so a signal that ran to +8R and round-tripped
      shows its round-tripped number forever and a winner is never booked.

  PLAN-FOLLOWED (plan_followed_R and friends)
      What you would actually have, had you taken the mechanical plan:
      filled at the NEXT session's open, stop where the alert said, two-lot
      management (partial at +2.5R, stop to breakeven at +1.5R, trading lot
      trails the 50-DMA, core lot exits on a weekly close below the 150-DMA),
      gap-throughs booked at the actual gap fill, costs applied. THIS is the
      number comparable to the backtest's +1.67R, and it is the one the brief
      nominates as the gate for scaling real capital.

It is computed by replaying each signal through backtest/engine.py itself —
the same code that produced +1.67R — rather than re-implementing the exit
rules here, so the two can never drift apart.

UNSIZED SIGNALS. When 2.5xATR is wider than the 12% hard cap the risk engine
SKIPS the name (Design Law #7) and the alert carries no stop. Those rows used
to carry no R at all and so were invisible in every expectancy figure — and
they are not a random sample: they are the most volatile names, which is
where a 30%-win / 9.6:1-payoff strategy keeps its right tail. They are now
measured against a REFERENCE stop (2.5xATR, cap lifted for measurement only)
and flagged `sized=False`. A reference stop is not a recommendation; the live
system still skips these names. It exists so the forward record can tell you
what skipping them costs or saves.
"""

from __future__ import annotations

import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backtest.engine import generate_signals, run_backtest
from backtest.metrics import apply_costs
from config import BUY_ALERT_KINDS, RISK
from data.cache import load_ohlcv

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JOURNAL = os.path.join(ROOT, "journal", "signals_journal.csv")
OUT = os.path.join(ROOT, "journal", "journal_outcomes.csv")

# history each replay needs behind the alert: 200-DMA warmup + 52-week
# high/low + the VCP window, with room to spare
_WARMUP_BARS = 400
# generous cap used ONLY to measure the names the live engine skips
_MEASURE_STOP_CAP_PCT = 60.0

_SIG_CACHE: dict[str, pd.DataFrame] = {}


def _signals_for(sym: str) -> pd.DataFrame | None:
    """generate_signals output for a symbol, computed once per run."""
    if sym in _SIG_CACHE:
        return _SIG_CACHE[sym]
    df = load_ohlcv(sym)
    if df is None or len(df) < 60:
        _SIG_CACHE[sym] = None
        return None
    try:
        sig = generate_signals(df.copy(), 1.0)
    except Exception:  # noqa: BLE001 — one bad series must not kill the report
        sig = None
    _SIG_CACHE[sym] = sig
    return sig


def _plan_followed(sym: str, alert_date: pd.Timestamp,
                   stop_price: float | None) -> dict:
    """Replay ONE signal through the real backtest engine.

    Entry is forced onto the first session strictly after the alert (the alert
    is written post-close, so its own close was never available), filled at
    that bar's OPEN — the stress-validated fill. Everything after that is the
    engine's own two-lot management.
    """
    sig = _signals_for(sym)
    if sig is None or sig.empty:
        return {}
    sig = sig.copy()

    after = sig.index[sig["date"] > alert_date]
    if not len(after):
        return {"plan_status": "not filled yet"}
    entry_i = after[0]

    # keep only the history the replay needs, then make this the ONLY entry
    start_i = max(0, entry_i - _WARMUP_BARS)
    sig = sig.iloc[start_i:].reset_index(drop=True)
    entry_i -= start_i
    sig["breakout_today"] = False
    sig.loc[entry_i, "breakout_today"] = True

    entry_open = float(sig["open"].iloc[entry_i])
    if not (entry_open > 0):
        return {"plan_status": "no open price"}

    sized = stop_price is not None and 0 < stop_price < entry_open
    if not sized:
        atr = sig["atr"].iloc[entry_i]
        if pd.isna(atr) or atr <= 0:
            return {"plan_status": "no stop, no ATR"}
        stop_price = entry_open - RISK.atr_stop_mult * float(atr)
        if stop_price <= 0:
            return {"plan_status": "no usable reference stop"}
    # the engine reads a per-signal stop from this column (EP class uses it)
    sig["stop_override"] = pd.NA
    sig.loc[entry_i, "stop_override"] = stop_price

    trades, _ = run_backtest(
        {sym: sig},
        entry_price_col="open",       # next session's open — the honest fill
        stop_fill="gap_aware",        # F3: gap-throughs fill at the open, not -1.0R
        size_on="equity",
        max_stop_pct=_MEASURE_STOP_CAP_PCT if not sized else None,
    )
    if trades.empty:
        return {"plan_status": "engine took no position"}
    trades = apply_costs(trades)

    # blended R across both lots, weighted by shares (the engine reports one
    # row per lot by design — Design Law #2 — so report the lots too)
    denom = float((trades["shares"] * trades["risk_per_share"]).sum())
    blended = (float(trades["realized_pnl_after_costs"].sum()) / denom
               if denom > 0 else None)

    def _lot(name: str, col: str):
        row = trades[trades["lot"] == name]
        return round(float(row[col].iloc[0]), 3) if len(row) else ""

    reasons = sorted(set(trades["exit_reason"]))
    still_open = "backtest_end" in reasons
    return {
        "plan_entry_date": str(pd.Timestamp(sig["date"].iloc[entry_i]).date()),
        "plan_entry_price": round(entry_open, 2),
        "plan_stop": round(float(stop_price), 2),
        "plan_sized": sized,
        "plan_followed_R": round(blended, 3) if blended is not None else "",
        "plan_R_trading_lot": _lot("trading", "r_multiple_after_costs"),
        "plan_R_core_lot": _lot("core", "r_multiple_after_costs"),
        "plan_exit_reasons": "; ".join(reasons),
        "plan_status": "open" if still_open else "closed",
    }


def main() -> None:
    if not os.path.exists(JOURNAL):
        print("no journal yet — outcomes will exist once the first alert is logged")
        return
    j = pd.read_csv(JOURNAL, parse_dates=["logged_at"])
    buys = j[j["kind"].isin(BUY_ALERT_KINDS)].copy()
    if buys.empty:
        print("journal has no buy-type signals yet")
        return

    rows = []
    for _, r in buys.iterrows():
        sym = r["symbol"]
        df = load_ohlcv(sym)
        if df is None:
            continue
        after = df[df["date"] > r["logged_at"]]
        entry = float(r["close"])
        stop = float(r["stop_suggested"]) if pd.notna(r["stop_suggested"]) and r["stop_suggested"] != "" else None
        risk = (entry - stop) if stop else None

        if after.empty:
            rows.append({**r.to_dict(), "days_elapsed": 0, "status": "no data yet"})
            continue

        hit_stop = bool(stop and (after["low"] <= stop).any())
        stop_hit_date = after.loc[after["low"] <= stop, "date"].iloc[0] if hit_stop else None
        # favorable excursion measured only until the stop was hit (if it was)
        favorable_window = after[after["date"] <= stop_hit_date] if hit_stop else after
        max_fav_r = (float(favorable_window["high"].max()) - entry) / risk if risk else None
        # adverse excursion mirrors the favorable one: the worst low reached
        # over the same window, expressed in R against the suggested-stop risk
        # (negative). Feeds future stop-width study — DISPLAY ONLY, no stop
        # change now. A stopped trade lands at/below -1R (gap-throughs < -1R).
        max_adv_r = (float(favorable_window["low"].min()) - entry) / risk if risk else None
        last_close = float(after["close"].iloc[-1])

        row = {
            **r.to_dict(),
            "days_elapsed": int((after["date"].iloc[-1] - r["logged_at"]).days),
            "return_to_date_pct": round((last_close / entry - 1) * 100, 2),
            "max_favorable_R": round(max_fav_r, 2) if max_fav_r is not None else "",
            "max_adverse_R": round(max_adv_r, 2) if max_adv_r is not None else "",
            "hit_suggested_stop": hit_stop,
            "r_to_date": round((last_close - entry) / risk, 2) if risk and not hit_stop else (-1.0 if hit_stop else ""),
            "status": "stopped" if hit_stop else "open",
        }
        try:
            row.update(_plan_followed(sym, r["logged_at"], stop))
        except Exception as e:  # noqa: BLE001 — the raw read must still publish
            row["plan_status"] = f"replay failed: {str(e)[:60]}"
        rows.append(row)

    out = pd.DataFrame(rows)
    out.to_csv(OUT, index=False)
    closed = out[out["status"] == "stopped"]
    open_ = out[out["status"] == "open"]
    print(f"{len(out)} buy signals tracked -> {OUT}")
    print(f"  open: {len(open_)}  stopped: {len(closed)}")
    if len(out):
        r_vals = pd.to_numeric(out["r_to_date"], errors="coerce").dropna()
        if len(r_vals):
            print(f"  RAW (mark-to-market, stop booked at -1R, alert-close entry):")
            print(f"    {r_vals.mean():+.2f}R across {len(r_vals)} signals "
                  f"— NOT comparable to the backtest")
        if "plan_followed_R" in out.columns:
            p = pd.to_numeric(out["plan_followed_R"], errors="coerce")
            sized = out.get("plan_sized")
            print("  PLAN-FOLLOWED (next-open fill, two-lot exits, "
                  "gap-aware stops, costs):")
            for label, mask in (("all", p.notna()),
                                ("sized only", p.notna() & (sized == True)),      # noqa: E712
                                ("unsized (reference stop)", p.notna() & (sized == False))):  # noqa: E712
                v = p[mask]
                if len(v):
                    print(f"    {label:<26} {v.mean():+.2f}R  n={len(v)}  "
                          f"median {v.median():+.2f}R  best {v.max():+.2f}R")
            print("    ^ this is the number comparable to the backtest's +1.67R")


if __name__ == "__main__":
    main()
