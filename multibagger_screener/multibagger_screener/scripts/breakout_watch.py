"""
scripts/breakout_watch.py — the 3:10 PM breakout check.

WHY (REVIEW_2026-09-25, gap 1). The validated entry is a CLOSE above the pivot
on >= 1.5x average volume. Buying at that close instead of the next morning's
open was worth ~10 points a year in the honest re-run — more than every scoring
layer combined. The nightly scan cannot deliver it: its earliest slot is 15:50
IST, after the close. So this job looks at tonight's candidates DURING the last
half hour — price against the pivot, and volume so far projected to the full
session — and tells the phone which names are breaking out while there is
still time to buy (NSE's official close is the volume-weighted price of
15:00-15:30, so an order at ~15:20 fills close to it).

MEASURED BEFORE TRUSTED: scripts/measure_intraday_proxy.py scores exactly this
decision against the official close on the real nightly candidates (git history
of state/trigger_state.json) — precision, recall, and the gap between a 15:20
fill and the close. Its numbers are in research/out/intraday_proxy.json and
the volume-pace table below comes from it.

SIDE EFFECTS, deliberately few: it reads the candidate list from the PUBLIC
repository (no git operation on this machine — a second laptop writer is how
the tree wedged before), fetches quotes from Yahoo, sends ONE Telegram message
to the owner chat, and appends its calls to logs/breakout_watch.csv (local,
gitignored) so the forward record can be scored later. It never touches the
journal, the scan state or the price cache.

    python scripts/breakout_watch.py              # the live check (15:00-15:27 IST only)
    python scripts/breakout_watch.py --dry-run    # print, send nothing
    python scripts/breakout_watch.py --force      # ignore the time window (testing)
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import urllib.request
from datetime import datetime, time as dtime

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

for _s in (sys.stdout, sys.stderr):          # the phone text has ₹ and arrows
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

TRIGGERS_URL = ("https://raw.githubusercontent.com/kartikeyaav/Golden-Stock/master/"
                "multibagger_screener/multibagger_screener/state/trigger_state.json")
LOCAL_TRIGGERS = os.path.join(ROOT, "state", "trigger_state.json")
LOG = os.path.join(ROOT, "logs", "breakout_watch.csv")

WINDOW = (dtime(15, 0), dtime(15, 27))       # act only inside this; a late wake-up exits
VOL_MULT = 1.5                               # config.TECHNICAL.breakout_volume_multiple
BUY_ZONE = 1.05                              # above pivot x 1.05 = extended, do not chase

# Share of the OFFICIAL session volume printed by each time (IST), median over
# 2,786 candidate-days (40 nightly lists, 2026-07-31 -> 09-25), measured by
# scripts/measure_intraday_proxy.py on 2026-09-26 (research/out/intraday_proxy.json).
# Yahoo's whole-day bars carry ~96% of NSE's official volume, which is already
# inside these ratios. On that sample the 15:10 call (price above pivot, volume
# on pace for >= 1.5x) matched the official close 95% of the time (precision)
# and caught 92% of the validated breakouts (recall); a 15:20 fill landed a
# median 0.00% from the official close.
VOLUME_CURVE = {
    "14:30": 0.7208, "14:45": 0.7570, "15:00": 0.8028, "15:05": 0.8244,
    "15:10": 0.8558, "15:15": 0.8840, "15:20": 0.9043, "15:25": 0.9246,
}


def volume_share(bar_end: dtime) -> float | None:
    """Interpolated share of the day's volume done by `bar_end`."""
    pts = sorted((dtime.fromisoformat(k), v) for k, v in VOLUME_CURVE.items() if v)
    if not pts:
        return None
    if bar_end <= pts[0][0]:
        return pts[0][1]
    for (t0, v0), (t1, v1) in zip(pts, pts[1:]):
        if t0 <= bar_end <= t1:
            span = (t1.hour * 60 + t1.minute) - (t0.hour * 60 + t0.minute)
            pos = (bar_end.hour * 60 + bar_end.minute) - (t0.hour * 60 + t0.minute)
            return v0 + (v1 - v0) * pos / span
    return pts[-1][1]


def load_candidates() -> tuple[dict, str, str]:
    """(triggers, scan_date, source). The public repo first — it is what the
    cloud committed last night — then the local copy."""
    try:
        with urllib.request.urlopen(TRIGGERS_URL, timeout=20) as r:
            d = json.loads(r.read())
        src = "github"
    except Exception:  # noqa: BLE001
        with open(LOCAL_TRIGGERS, encoding="utf-8") as f:
            d = json.load(f)
        src = "local copy"
    trig = {s: t for s, t in (d.get("triggers") or {}).items()
            if (t or {}).get("status") == "AWAITING TRIGGER" and (t or {}).get("pivot")}
    return trig, str(d.get("date") or ""), src


def yahoo(sym: str, manifest: dict) -> str:
    return manifest.get(sym, {}).get("yahoo_symbol") or f"{sym}.NS"


def fetch(symbols: list[str], replay: bool = False) -> tuple[dict, dict]:
    """daily history (6 months) and today's 5-minute bars, per NSE symbol
    (the last five sessions' bars when replaying a past day)."""
    import yfinance as yf
    man_p = os.path.join(ROOT, "data_cache", "manifest.json")
    manifest = json.load(open(man_p, encoding="utf-8")) if os.path.exists(man_p) else {}
    tick = {yahoo(s, manifest): s for s in symbols}
    daily, intra = {}, {}
    D = yf.download(list(tick), period="6mo", interval="1d", group_by="ticker",
                    auto_adjust=False, threads=True, progress=False)
    I = yf.download(list(tick), period="5d" if replay else "1d", interval="5m", group_by="ticker",
                    auto_adjust=False, threads=True, progress=False)
    for yh, sym in tick.items():
        for src, dst in ((D, daily), (I, intra)):
            try:
                x = src[yh].dropna(how="all")
            except KeyError:
                continue
            if not x.empty:
                dst[sym] = x
    return daily, intra


def assess(sym: str, pivot: float, d: pd.DataFrame, bars: pd.DataFrame, now: datetime) -> dict | None:
    """One candidate at this moment. `d` = daily bars (the last row may be
    today's partial bar, which is dropped), `bars` = today's 5-minute bars."""
    idx = bars.index
    if getattr(idx, "tz", None) is not None:
        idx = idx.tz_convert("Asia/Kolkata").tz_localize(None)
    bars = bars.set_axis(idx)
    today = now.date()
    bars = bars[bars.index.date == today]
    if bars.empty:
        return None
    hist = d[d.index.date < today] if hasattr(d.index, "date") else d
    if len(hist) < 55:
        return None
    avg50 = float(hist["Volume"].tail(50).mean())
    last_bar = bars.index[-1]
    bar_end = (last_bar + pd.Timedelta(minutes=5)).time()
    share = volume_share(bar_end)
    if not share or avg50 <= 0:
        return None
    v = float(bars["Volume"].sum())
    px = float(bars["Close"].iloc[-1])
    pace = v / share / avg50
    h, l, c = hist["High"], hist["Low"], hist["Close"]
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    atr = float(tr.tail(14).mean())
    return {"sym": sym, "pivot": pivot, "px": px, "pace": pace, "avg50": avg50,
            "vol": v, "bar": last_bar.strftime("%H:%M"), "atr": atr,
            "above": px > pivot, "extended": px > pivot * BUY_ZONE,
            "confirmed": px > pivot and pace >= VOL_MULT}


def plan_for(a: dict) -> dict:
    """The same paper plan the Setups page shows (dashboard_extras.build_setups)."""
    try:
        from scoring.regime import market_risk_scale
        from scoring.technical_score import compute_entry_plan
        p = compute_entry_plan(a["pivot"], a["atr"], risk_scale=market_risk_scale())
        if p.get("skip"):
            return {"skip": str(p.get("skip_reason", ""))[:80]}
        return {"stop": p["stop_loss_price"], "shares": p["shares_total"]}
    except Exception as e:  # noqa: BLE001
        return {"skip": f"no plan ({type(e).__name__})"}


def _inr(x: float) -> str:
    return f"₹{x:,.2f}" if x < 100 else f"₹{x:,.1f}"


def message(res: list[dict], scan_date: str, n_watched: int, stamp: str, stale_note: str) -> str:
    buy = [r for r in res if r["confirmed"] and not r["extended"]]
    ext = [r for r in res if r["confirmed"] and r["extended"]]
    short = [r for r in res if r["above"] and not r["confirmed"]]
    L = [f"GOLDEN STOCK — {stamp} breakout check", ""]
    if stale_note:
        L += [f"⚠️ {stale_note}", ""]
    if buy:
        L.append("BREAKING OUT NOW — a close above the pivot on volume is the validated entry; buy before 15:25")
        for r in sorted(buy, key=lambda r: -r["pace"]):
            pl = r.get("plan") or {}
            tail = (f" · stop {_inr(pl['stop'])} · {pl['shares']} sh (paper plan)" if "stop" in pl
                    else f" · {pl.get('skip', 'no plan')}")
            L.append(f"• {r['sym']} {_inr(r['px'])} vs pivot {_inr(r['pivot'])} "
                     f"(+{(r['px'] / r['pivot'] - 1) * 100:.1f}%) · volume on pace for "
                     f"{r['pace']:.1f}×{tail}")
        L.append("")
    if short:
        L.append("ABOVE THE PIVOT, VOLUME SHORT — not confirmed, do not buy yet")
        for r in sorted(short, key=lambda r: -r["pace"])[:6]:
            L.append(f"• {r['sym']} {_inr(r['px'])} vs {_inr(r['pivot'])} · on pace for {r['pace']:.1f}×")
        L.append("")
    if ext:
        L.append(f"EXTENDED (> {int((BUY_ZONE - 1) * 100)}% above pivot) — do not chase")
        for r in ext[:6]:
            L.append(f"• {r['sym']} {_inr(r['px'])} vs {_inr(r['pivot'])} (+{(r['px'] / r['pivot'] - 1) * 100:.1f}%)")
        L.append("")
    if not (buy or short or ext):
        L.append(f"No candidate is above its pivot ({n_watched} watched).")
        L.append("")
    L.append(f"Candidates from the {scan_date} scan · quotes via Yahoo, latest bar {res[0]['bar'] if res else '—'}")
    return "\n".join(L)


def log_rows(res: list[dict], stamp: str) -> None:
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    new = not os.path.exists(LOG)
    with open(LOG, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["run_at", "sym", "pivot", "px", "pace", "bar", "above", "extended", "confirmed"])
        for r in res:
            w.writerow([stamp, r["sym"], r["pivot"], round(r["px"], 2), round(r["pace"], 3),
                        r["bar"], r["above"], r["extended"], r["confirmed"]])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--as-of", default="", help="replay 'YYYY-MM-DD HH:MM' from Yahoo's recent "
                    "bars (testing; implies --dry-run and --force)")
    a = ap.parse_args()
    now = datetime.now()
    if a.as_of:
        now = datetime.fromisoformat(a.as_of)
        a.dry_run = a.force = True
    if not a.force and (now.weekday() > 4 or not (WINDOW[0] <= now.time() <= WINDOW[1])):
        print(f"{now:%Y-%m-%d %H:%M} outside {WINDOW[0]}-{WINDOW[1]} on a weekday — nothing to do")
        return 0
    if not any(VOLUME_CURVE.values()):
        print("volume curve not measured yet — run scripts/measure_intraday_proxy.py first")
        return 1
    trig, scan_date, src = load_candidates()
    stale_note = ""
    try:
        age = (now.date() - datetime.fromisoformat(scan_date).date()).days
        if age > 4:
            stale_note = f"candidate list is from {scan_date} ({age} days old) — the nightly scan may be failing"
    except ValueError:
        stale_note = "candidate list has no date"
    syms = sorted(trig)
    daily, intra = fetch(syms, replay=bool(a.as_of))
    if a.as_of:                      # keep only bars that had finished by `now`
        cut = pd.Timestamp(now) - pd.Timedelta(minutes=5)
        for s_, b in list(intra.items()):
            ix = b.index.tz_convert("Asia/Kolkata").tz_localize(None) if b.index.tz is not None else b.index
            intra[s_] = b[ix <= cut]
    res = []
    for s in syms:
        if s in daily and s in intra:
            r = assess(s, float(trig[s]["pivot"]), daily[s], intra[s], now)
            if r:
                res.append(r)
    for r in res:
        if r["confirmed"] and not r["extended"]:
            r["plan"] = plan_for(r)
    stamp = f"{now:%a %d %b %H:%M}"
    text = message(res, scan_date, len(syms), stamp, stale_note)
    print(text)
    print(f"\n[{len(res)}/{len(syms)} candidates quoted; source: {src}]")
    if not a.as_of:
        log_rows(res, now.strftime("%Y-%m-%d %H:%M"))
    if a.dry_run:
        return 0
    from send_telegram import load_config, send_message
    cfg = load_config()
    if not cfg:
        print("TELEGRAM_BOT_TOKEN/CHAT_ID not set — printed, not sent")
        return 0
    send_message(*cfg, text)
    print("sent")
    return 0


RUN_LOG = os.path.join(ROOT, "logs", "breakout_watch.log")


class _Tee:
    """Scheduled runs use pythonw (no console flashing up at 15:10), which has
    no stdout — and pythonw swallowing a traceback is one of the ways a laptop
    job has failed silently here before. Everything printed, and any crash,
    also goes to logs/breakout_watch.log."""

    def __init__(self, stream, fh):
        self.stream, self.fh = stream, fh

    def write(self, x):
        self.fh.write(x)
        if self.stream is not None:
            try:
                self.stream.write(x)
            except Exception:  # noqa: BLE001
                pass

    def flush(self):
        self.fh.flush()
        if self.stream is not None:
            try:
                self.stream.flush()
            except Exception:  # noqa: BLE001
                pass


if __name__ == "__main__":
    os.makedirs(os.path.dirname(RUN_LOG), exist_ok=True)
    with open(RUN_LOG, "a", encoding="utf-8") as _fh:
        _fh.write(f"\n===== {datetime.now():%Y-%m-%d %H:%M:%S} {' '.join(sys.argv[1:])}\n")
        _out, _err = sys.stdout, sys.stderr
        sys.stdout = _Tee(_out, _fh)
        sys.stderr = _Tee(_err, _fh)
        try:
            code = main()
        except Exception:  # noqa: BLE001
            import traceback
            traceback.print_exc()
            code = 1
        finally:
            # restore before the log closes: interpreter shutdown flushes
            # sys.stdout, and a closed log there turns exit 0 into exit 120
            sys.stdout.flush()
            sys.stdout, sys.stderr = _out, _err
        _fh.write(f"exit {code}\n")
    raise SystemExit(code)
