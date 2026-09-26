"""
scripts/measure_intraday_proxy.py — does a 3:10 PM reading predict the
validated breakout well enough to buy on it?

THE QUESTION (REVIEW_2026-09-25 gap 1). The validated entry is a CLOSE above the
pivot on >= 1.5x average volume, and buying at that close instead of the next
morning's open was worth ~10 points a year in the re-run. The nightly scan runs
at 15:50 IST at the earliest — after the close — so the only way to buy at the
close is to decide BEFORE it, at ~15:10, on partial information: the price so
far and the volume so far. This script measures how often that decision agrees
with the official close, on the real candidates.

Candidates are the real ones: every nightly `state/trigger_state.json` the cloud
committed (git history), AWAITING TRIGGER names with a pivot. For session d the
list is the one committed after session d-1. Truth is NSE's official close and
volume for d (the bhavcopy); the 15:10 view is Yahoo's 5-minute bars up to 15:10.

NSE's official close is the volume-weighted price of 15:00-15:30, not the last
trade, so a 15:20 buy is close to a close fill. The script reports that gap too.

    python scripts/measure_intraday_proxy.py
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import date, time as dtime
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(os.path.dirname(ROOT))
sys.path.insert(0, ROOT)

from data import nse_history as H  # noqa: E402

INTRA = H.HIST_DIR.parent / "intraday5m"
REL = "multibagger_screener/multibagger_screener/state/trigger_state.json"
VOL_MULT = 1.5
CHECK_AT = dtime(15, 10)          # bars that START before 15:10 are known at 15:10
FILL_AT = dtime(15, 20)           # the price a 15:20 order would get: the 15:15 bar's close
CURVE_AT = ("14:30", "14:45", "15:00", "15:05", "15:10", "15:15", "15:20", "15:25", "15:30")


def trigger_history() -> dict[str, dict]:
    """scan date -> {sym: pivot} for AWAITING TRIGGER names, last commit per date."""
    log = subprocess.run(["git", "log", "--format=%h", "--", REL], cwd=REPO,
                         capture_output=True, text=True, check=True).stdout.split()
    out = {}
    for h in reversed(log):                      # oldest first; later commits overwrite
        raw = subprocess.run(["git", "show", f"{h}:{REL}"], cwd=REPO,
                             capture_output=True, text=True).stdout
        try:
            d = json.loads(raw)
        except json.JSONDecodeError:
            continue
        piv = {s: float(t["pivot"]) for s, t in (d.get("triggers") or {}).items()
               if (t or {}).get("status") == "AWAITING TRIGGER" and (t or {}).get("pivot")}
        if d.get("date") and piv:
            out[d["date"]] = piv
    return out


def daily_official(days: list[date]) -> dict[date, pd.DataFrame]:
    out = {}
    for d in days:
        p = H.bhav_path(d)
        if p.exists():
            b = H.parse_bhav(p, d)
            b = b[b["series"].isin(H.EQUITY_SERIES)].drop_duplicates("symbol")
            out[d] = b.set_index("symbol")[["open", "high", "low", "close", "volume"]]
    return out


def intraday(sym: str) -> pd.DataFrame | None:
    p = INTRA / f"{sym}.csv"
    if not p.exists():
        return None
    df = pd.read_csv(p, parse_dates=["ts"])
    df["d"] = df["ts"].dt.date
    df["t"] = df["ts"].dt.time
    return df


def main() -> int:
    hist = trigger_history()
    # sessions = weekdays whose bhavcopy is on disk (the status file is only
    # flushed every 200 downloads, so it can lag the files themselves)
    sessions = [d for d in H._weekdays(date(2026, 3, 1), date.today()) if H.bhav_path(d).exists()]
    off = daily_official(sessions)
    sess = sorted(off)
    print(f"{len(hist)} nightly candidate lists; {len(sess)} official sessions "
          f"{sess[0]} -> {sess[-1]}", flush=True)

    # average volume over the 50 sessions before each day, from the official files
    vol = pd.DataFrame({d: off[d]["volume"] for d in sess}).T.sort_index()
    avg50 = vol.rolling(50, min_periods=40).mean().shift(1)

    rows, frac = [], []
    cache: dict[str, pd.DataFrame | None] = {}
    for scan_date, piv in sorted(hist.items()):
        sd = date.fromisoformat(scan_date)
        nxt = [d for d in sess if d > sd]
        if not nxt:
            continue
        d = nxt[0]
        for sym, pivot in piv.items():
            if sym not in off[d].index or d not in avg50.index or sym not in avg50.columns:
                continue
            a50 = avg50.at[d, sym]
            if not np.isfinite(a50) or a50 <= 0:
                continue
            if sym not in cache:
                cache[sym] = intraday(sym)
            ib = cache[sym]
            if ib is None:
                continue
            day = ib[ib["d"] == d]
            if len(day) < 60:                     # a full session is 75 bars
                continue
            pre = day[day["t"] < CHECK_AT]
            fill = day[day["t"] < FILL_AT]
            if pre.empty or fill.empty:
                continue
            o = off[d].loc[sym]
            v1510 = float(pre["volume"].sum())
            ytot = float(day["volume"].sum())
            if o["volume"] > 0:
                frac.append((v1510 / o["volume"], ytot / o["volume"]))
            cum = {k: float(day.loc[day["t"] < dtime.fromisoformat(k), "volume"].sum())
                   for k in CURVE_AT}
            rows.append({"date": d, "sym": sym, "pivot": pivot, "a50": a50,
                         **{f"by{k.replace(':', '')}": cum[k] for k in CURVE_AT},
                         "px1510": float(pre["close"].iloc[-1]), "v1510": v1510,
                         "px1520": float(fill["close"].iloc[-1]),
                         "close": float(o["close"]), "volume": float(o["volume"]),
                         "high": float(o["high"])})
    df = pd.DataFrame(rows)
    fr = pd.DataFrame(frac, columns=["by1510", "yahoo_total"])
    f_med = float(fr["by1510"].median())
    print(f"candidate-days {len(df):,}; share of the official day's volume printed by 15:10: "
          f"median {f_med:.3f} (IQR {fr['by1510'].quantile(.25):.3f}-{fr['by1510'].quantile(.75):.3f}); "
          f"Yahoo's whole-day volume / NSE's: median {fr['yahoo_total'].median():.3f}")

    # the volume-pace table breakout_watch.py projects with: share of the
    # OFFICIAL session volume printed by each time (Yahoo bars, NSE total)
    curve = {k: round(float((df[f"by{k.replace(':', '')}"] / df["volume"]).median()), 4)
             for k in CURVE_AT}
    print("volume share by time (median):", curve)
    df["truth"] = (df["close"] > df["pivot"]) & (df["volume"] >= VOL_MULT * df["a50"])
    df["proj"] = df["v1510"] / f_med
    df["call"] = (df["px1510"] > df["pivot"]) & (df["proj"] >= VOL_MULT * df["a50"])
    tp = int((df["call"] & df["truth"]).sum())
    fp = int((df["call"] & ~df["truth"]).sum())
    fn = int((~df["call"] & df["truth"]).sum())
    prec = tp / max(tp + fp, 1)
    rec = tp / max(tp + fn, 1)
    print(f"validated breakouts at the close: {int(df['truth'].sum())}; 15:10 calls: "
          f"{int(df['call'].sum())}  ->  precision {prec:.0%}, recall {rec:.0%}  (TP {tp}, FP {fp}, FN {fn})")

    # what a false call costs: where did those names close vs the 15:20 fill?
    fpd = df[df["call"] & ~df["truth"]]
    tpd = df[df["call"] & df["truth"]]
    gap_tp = (tpd["close"] / tpd["px1520"] - 1) * 100
    gap_fp = (fpd["close"] / fpd["px1520"] - 1) * 100
    below = fpd["close"] <= fpd["pivot"]
    print(f"true calls: official close vs a 15:20 fill, median {gap_tp.median():+.2f}% "
          f"(IQR {gap_tp.quantile(.25):+.2f} .. {gap_tp.quantile(.75):+.2f})")
    print(f"false calls: {int(below.sum())} closed back at/below the pivot, "
          f"{int((~below).sum())} closed above it on short volume; close vs fill median "
          f"{gap_fp.median():+.2f}%")

    # threshold sensitivity: a stricter 15:10 volume bar trades recall for precision
    sens = []
    for m in (1.2, 1.5, 1.8, 2.0, 2.5):
        call = (df["px1510"] > df["pivot"]) & (df["proj"] >= m * df["a50"])
        t_, f_, n_ = (call & df["truth"]).sum(), (call & ~df["truth"]).sum(), (~call & df["truth"]).sum()
        sens.append({"proj_mult": m, "precision": round(t_ / max(t_ + f_, 1), 3),
                     "recall": round(t_ / max(t_ + n_, 1), 3), "calls": int(call.sum())})
    print(pd.DataFrame(sens).to_string(index=False))

    out = {"measured": str(date.today()), "candidate_days": int(len(df)),
           "sessions": [str(sess[0]), str(sess[-1])], "volume_share_by_1510": round(f_med, 4),
           "yahoo_over_nse_volume": round(float(fr["yahoo_total"].median()), 4),
           "volume_curve": curve,
           "truth": int(df["truth"].sum()), "calls": int(df["call"].sum()),
           "precision": round(prec, 3), "recall": round(rec, 3),
           "fill_gap_true_median_pct": round(float(gap_tp.median()), 3) if len(gap_tp) else None,
           "false_calls_closed_below_pivot": int(below.sum()), "sensitivity": sens}
    Path(ROOT, "research", "out").mkdir(parents=True, exist_ok=True)
    with open(os.path.join(ROOT, "research", "out", "intraday_proxy.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)
    df.to_csv(os.path.join(ROOT, "research", "out", "intraday_proxy_rows.csv"), index=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
