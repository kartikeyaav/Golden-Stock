"""
scripts/multibagger_sleeve.py — the multibagger sleeve, run forward on paper
(PREREG_2026-09-27_multibagger_sleeve.md). Runs after the radar, nightly.

The trading logic is NOT reimplemented here: it is research/sim.py's Book, the
object the backtest loops over (its equivalence to the measured simulator was
checked: identical final value, trades and equity curve on three
configurations). Each night:

  1. uses the whole-market panel the radar built (building it if this slot's
     runner has none),
  2. restores the Book from state/multibagger_sleeve.json and re-anchors each
     position's entry date to tonight's grid,
  3. steps the Book over every session since the last one it processed —
     a missed night is caught up, a re-run is a no-op,
  4. appends every fill to journal/multibagger_sleeve_ledger.csv and the NAV
     to the state.

The cloud is the only writer (daily.yml commits both files).

    python scripts/multibagger_sleeve.py            # nightly
    python scripts/multibagger_sleeve.py --status   # print, change nothing
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from datetime import date, datetime

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from research.sim import Book, Context, SimConfig  # noqa: E402

REGISTERED = "2026-09-27"
STATE = os.path.join(ROOT, "state", "multibagger_sleeve.json")
LEDGER = os.path.join(ROOT, "journal", "multibagger_sleeve_ledger.csv")
LEDGER_FIELDS = ["date", "symbol", "action", "shares", "price", "value", "reason"]
# PREREG_2026-09-27 §2 — frozen
CFG = SimConfig(max_positions=5, fill="open", exit="sma", trail=150, stop_pct=0.20,
                min_hold=20, cost_pct=0.25, liq_cap=0.05, start_cash=1_000_000.0)


def breadth_risk_on(g) -> np.ndarray:
    """R-B: at least 50% of universe members close above their own 200-day
    average (and at least 100 members are measurable)."""
    U = g.universe()
    s200 = g.sma(200)
    ok = U & np.isfinite(s200)
    n = ok.sum(axis=1)
    frac = ((g.c > s200) & ok).sum(axis=1) / np.maximum(n, 1)
    return (frac >= 0.5) & (n >= 100)


def load_state() -> dict:
    try:
        with open(STATE, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {"registered": REGISTERED, "capital": CFG.start_cash, "nav": [], "last_session": None,
                "book": None}


def save_state(st: dict) -> None:
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    tmp = STATE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(st, f, indent=1, default=float)
    os.replace(tmp, STATE)


def append_ledger(rows: list[dict]) -> None:
    if not rows:
        return
    os.makedirs(os.path.dirname(LEDGER), exist_ok=True)
    new = not os.path.exists(LEDGER)
    with open(LEDGER, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=LEDGER_FIELDS)
        if new:
            w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in LEDGER_FIELDS})


def advance(g, st: dict) -> tuple[dict, list[dict]]:
    """Step the sleeve over every session in `g` after the last one processed
    (and after registration). Pure apart from its inputs: tests drive it with
    synthetic grids."""
    from research.grid import xrank
    from research.hypotheses import h9_rs_leader
    U = g.universe()
    ctx = Context(g, h9_rs_leader(g) & U, xrank(g.ret(126), U), CFG, risk_on=breadth_risk_on(g))
    book = Book.from_state(CFG, st["book"]) if st.get("book") else Book(CFG)
    dates = g.dates
    for s, p in book.pos.items():                       # tonight's grid, tonight's indices
        d = p.get("entry_date")
        p["entry_t"] = int(np.searchsorted(dates.values, np.datetime64(d))) if d else 0
    after = st.get("last_session") or REGISTERED
    todo = [t for t in range(g.T) if str(dates[t].date()) > after]
    rows = []
    nav = st.setdefault("nav", [])
    for t in todo:
        held_before = set(book.pos)
        n_trades = len(book.trades)
        val = book.step(ctx, t, allow_entries=True)
        day = str(dates[t].date())
        for s in sorted(set(book.pos) - held_before):
            p = book.pos[s]
            p["entry_date"] = day
            rows.append({"date": day, "symbol": s.split("~")[0], "action": "BUY", "shares": p["sh"],
                         "price": round(p["px"], 2), "value": round(p["sh"] * p["px"], 2),
                         "reason": "RS leader: 6m and 12m return in the top 10%"})
        for tr in book.trades[n_trades:]:
            why = ("stopped trading (last price)" if tr.get("stale")
                   else "regime exit or stop / 30-week trail")
            rows.append({"date": day, "symbol": str(tr["sym"]).split("~")[0], "action": "SELL",
                         "shares": tr["sh"], "price": round(tr["exit_px"], 2),
                         "value": round(tr["sh"] * tr["exit_px"], 2),
                         "reason": f"{why}; x{tr['mult']:.2f} since {tr.get('entry_date', '')}"})
        nav.append([day, round(float(val), 2)])
        st["last_session"] = day
    book.trades = []                                     # the ledger is the record
    st["book"] = book.to_state()
    st["risk_on"] = bool(ctx.risk_on[-1]) if g.T else None
    st["asof"] = str(dates[-1].date()) if g.T else None
    return st, rows


def snapshot() -> dict:
    """What the dashboard shows: holdings, pending orders, NAV, and the forward
    comparison against the MIDSMALL ETF on the same dates."""
    st = load_state()
    book = st.get("book") or {}
    nav = st.get("nav") or []
    out = {"registered": st.get("registered"), "asof": st.get("asof"), "risk_on": st.get("risk_on"),
           "cash": (book or {}).get("cash"), "nav": nav,
           "holdings": [{"sym": s.split("~")[0], "since": p.get("entry_date"), "entry": p.get("px"),
                         "shares": p.get("sh"), "last": (book.get("last_px") or {}).get(s),
                         "ret_pct": round(((book.get("last_px") or {}).get(s, p["px"]) / p["px"] - 1) * 100, 1)}
                        for s, p in (book.get("pos") or {}).items()],
           "pending_buys": [s.split("~")[0] for s in book.get("pending_buys") or []],
           "pending_sells": [s.split("~")[0] for s in book.get("pending_sells") or []]}
    if nav:
        first, last = nav[0], nav[-1]
        out["since_pct"] = round((last[1] / CFG.start_cash - 1) * 100, 2)
        try:
            from data.cache import load_ohlcv
            b = load_ohlcv("MIDSMALL")
            s = b.set_index("date")["close"]
            s = s[s.index >= pd.Timestamp(first[0])]
            if len(s) >= 2:
                out["midsmall_pct"] = round((float(s.iloc[-1]) / float(s.iloc[0]) - 1) * 100, 2)
        except Exception:  # noqa: BLE001
            pass
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--status", action="store_true")
    a = ap.parse_args()
    if a.status:
        print(json.dumps(snapshot(), indent=1, default=str)[:4000])
        return 0
    import multibagger_radar as MR
    st = load_state()
    # the later catch-up slots: the radar already covers the latest session and
    # this sleeve already processed it -> nothing to do, and no rebuild of the
    # whole-market panel (the radar skipped it in this runner)
    try:
        with open(MR.STATE, encoding="utf-8") as f:
            radar_asof = json.load(f).get("asof")
    except (OSError, ValueError):
        radar_asof = None
    if radar_asof and st.get("last_session") and st["last_session"] >= radar_asof:
        print(f"multibagger sleeve already current ({st['last_session']}) — nothing to do")
        return 0
    if not MR.RADAR_PANEL.exists():
        MR.build_recent(date.today())
    from research.grid import load_grid
    g = load_grid(path=MR.RADAR_PANEL)
    before = st.get("last_session")
    st, rows = advance(g, st)
    st["generated"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    save_state(st)
    append_ledger(rows)
    book = st["book"]
    print(f"multibagger sleeve: sessions {before or REGISTERED} -> {st.get('last_session')}; "
          f"fills {len(rows)}; holdings {sorted(book['pos'])}; pending buys {book['pending_buys']}; "
          f"cash {book['cash']:,.0f}; regime {'on' if st.get('risk_on') else 'OFF'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
