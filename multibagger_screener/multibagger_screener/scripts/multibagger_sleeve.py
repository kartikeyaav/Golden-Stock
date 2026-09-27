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

Every other sleeve is a frozen spec on the same engine (SPECS below):
`--sleeve value_breakout` (cheap + new uptrend) and `--sleeve
promoter_momentum` (promoter buying + momentum, read from insider_archive.csv).

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

LEDGER_FIELDS = ["date", "symbol", "action", "shares", "price", "value", "reason"]
# Every sleeve is a frozen spec from its pre-registration; the engine is shared.
SPECS = {
    # PREREG_2026-09-27_multibagger_sleeve.md section 2
    "multibagger": {
        "registered": "2026-09-27",
        "state": os.path.join(ROOT, "state", "multibagger_sleeve.json"),
        "ledger": os.path.join(ROOT, "journal", "multibagger_sleeve_ledger.csv"),
        "cfg": SimConfig(max_positions=5, fill="open", exit="sma", trail=150, stop_pct=0.20,
                         min_hold=20, cost_pct=0.25, liq_cap=0.05, start_cash=1_000_000.0),
        "breadth_exit": True,
        "signal": "rs_leader", "reason": "RS leader: 6m and 12m return in the top 10%"},
    # PREREG_2026-09-27_value_breakout.md section 3
    "value_breakout": {
        "registered": "2026-09-27",
        "state": os.path.join(ROOT, "state", "value_breakout_sleeve.json"),
        "ledger": os.path.join(ROOT, "journal", "value_breakout_sleeve_ledger.csv"),
        "cfg": SimConfig(max_positions=10, fill="open", exit="sma", trail=150, stop_pct=0.20,
                         min_hold=20, cost_pct=0.25, liq_cap=0.05, start_cash=1_000_000.0),
        "breadth_exit": True,
        "signal": "value_breakout",
        "reason": "cheap (FCF yield and book-to-market top 30%) + a 2-year breakout or stage-2 start"},
    # PREREG_2026-09-28_promoter_momentum.md section 3: the cell chosen on
    # 2016-2020 by the rule registered in section 2 (research/promoter_momentum.py)
    "promoter_momentum": {
        "registered": "2026-09-28",
        "state": os.path.join(ROOT, "state", "promoter_momentum_sleeve.json"),
        "ledger": os.path.join(ROOT, "journal", "promoter_momentum_sleeve_ledger.csv"),
        "cfg": SimConfig(max_positions=5, fill="open", exit="chandelier", chandelier_k=3.0, stop_pct=0.20,
                         min_hold=20, cost_pct=0.25, liq_cap=0.05, start_cash=1_000_000.0),
        "breadth_exit": True,
        "signal": "promoter_momentum",
        "reason": "promoter market purchase disclosed in the last 60 sessions + RS leader or trend template"},
}
# the multibagger sleeve's names, kept for the tests and the dashboard
REGISTERED = SPECS["multibagger"]["registered"]
STATE = SPECS["multibagger"]["state"]
LEDGER = SPECS["multibagger"]["ledger"]
CFG = SPECS["multibagger"]["cfg"]
VALUE_TABLE = os.path.join(ROOT, "value_fundamentals.csv")
INSIDER_ARCHIVE = os.path.join(ROOT, "insider_archive.csv")


def load_insider_archive() -> pd.DataFrame:
    """The committed promoter / director / KMP trades (data/insider.py), each
    renamed symbol carried to today's name, exactly as the radar reads them."""
    tr = pd.read_csv(INSIDER_ARCHIVE, parse_dates=["disclosed_at"])
    try:
        from data.nse_history import _symbol_chain
        chain = _symbol_chain()
    except Exception:  # noqa: BLE001 — no chain = today's names only
        chain = {}
    tr["symbol"] = tr["symbol"].astype(str).str.strip().map(lambda s: chain.get(s, s))
    return tr


def signal_for(g, kind: str, table=None):
    """The frozen signal of a sleeve, from the research code. `table` is the
    sleeve's data file (value fundamentals, or insider trades) — tests pass a
    synthetic one; None reads the committed file."""
    from research.hypotheses import h9_rs_leader
    U = g.universe()
    if kind == "rs_leader":
        return h9_rs_leader(g) & U
    if kind == "value_breakout":
        from research import fundamentals as F
        from research.hypotheses import h2_multi_year_base_breakout, h5_stage2_start
        tab = table if table is not None else pd.read_csv(VALUE_TABLE)
        fg = F.grids_from_table(g, tab)
        return F.h20_cheap_new_uptrend(g, fg, h2_multi_year_base_breakout(g), h5_stage2_start(g)) & U
    if kind == "promoter_momentum":
        from research.insider_study import h25_grid
        tr = table if table is not None else load_insider_archive()
        return h25_grid(g, tr) & U
    raise ValueError(kind)


def breadth_risk_on(g) -> np.ndarray:
    """R-B: at least 50% of universe members close above their own 200-day
    average (and at least 100 members are measurable)."""
    U = g.universe()
    s200 = g.sma(200)
    ok = U & np.isfinite(s200)
    n = ok.sum(axis=1)
    frac = ((g.c > s200) & ok).sum(axis=1) / np.maximum(n, 1)
    return (frac >= 0.5) & (n >= 100)


def load_state(spec: str = "multibagger") -> dict:
    S = SPECS[spec]
    try:
        with open(S["state"], encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {"registered": S["registered"], "capital": S["cfg"].start_cash, "nav": [],
                "last_session": None, "book": None}


def save_state(st: dict, spec: str = "multibagger") -> None:
    path = SPECS[spec]["state"]
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(st, f, indent=1, default=float)
    os.replace(tmp, path)


def append_ledger(rows: list[dict], spec: str = "multibagger") -> None:
    if not rows:
        return
    path = SPECS[spec]["ledger"]
    os.makedirs(os.path.dirname(path), exist_ok=True)
    new = not os.path.exists(path)
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=LEDGER_FIELDS)
        if new:
            w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in LEDGER_FIELDS})


def advance(g, st: dict, spec: str = "multibagger", table=None) -> tuple[dict, list[dict]]:
    """Step a sleeve over every session in `g` after the last one processed
    (and after registration). Pure apart from its inputs: tests drive it with
    synthetic grids (and, for the value sleeve, a synthetic table)."""
    from research.grid import xrank
    S = SPECS[spec]
    cfg = S["cfg"]
    registered = REGISTERED if spec == "multibagger" else S["registered"]
    U = g.universe()
    if S["signal"] == "promoter_momentum":
        # the latest disclosure this night traded on: a feed NSE refuses shows
        # up as a date that stops moving, never as silence (PREREG_2026-09-28 §5)
        table = table if table is not None else load_insider_archive()
        st["insider_asof"] = str(table["disclosed_at"].max())[:16] if len(table) else None
    ctx = Context(g, signal_for(g, S["signal"], table), xrank(g.ret(126), U), cfg,
                  risk_on=breadth_risk_on(g) if S["breadth_exit"] else None)
    trail = "30-week trail" if cfg.exit == "sma" else f"{cfg.chandelier_k:g}xATR trail"
    book = Book.from_state(cfg, st["book"]) if st.get("book") else Book(cfg)
    dates = g.dates
    for s, p in book.pos.items():                       # tonight's grid, tonight's indices
        d = p.get("entry_date")
        p["entry_t"] = int(np.searchsorted(dates.values, np.datetime64(d))) if d else 0
    after = st.get("last_session") or registered
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
                         "reason": S["reason"]})
        for tr in book.trades[n_trades:]:
            why = ("stopped trading (last price)" if tr.get("stale")
                   else f"regime exit or stop / {trail}" if ctx.risk_on is not None
                   else f"stop / {trail}")
            rows.append({"date": day, "symbol": str(tr["sym"]).split("~")[0], "action": "SELL",
                         "shares": tr["sh"], "price": round(tr["exit_px"], 2),
                         "value": round(tr["sh"] * tr["exit_px"], 2),
                         "reason": f"{why}; x{tr['mult']:.2f} since {tr.get('entry_date', '')}"})
        nav.append([day, round(float(val), 2)])
        st["last_session"] = day
    book.trades = []                                     # the ledger is the record
    st["book"] = book.to_state()
    st["risk_on"] = bool(ctx.risk_on[-1]) if g.T and ctx.risk_on is not None else None
    st["asof"] = str(dates[-1].date()) if g.T else None
    return st, rows


def snapshot(spec: str = "multibagger") -> dict:
    """What the dashboard shows: holdings, pending orders, NAV, and the forward
    comparison against the MIDSMALL ETF on the same dates."""
    st = load_state(spec)
    book = st.get("book") or {}
    nav = st.get("nav") or []
    out = {"registered": st.get("registered"), "asof": st.get("asof"), "risk_on": st.get("risk_on"),
           "breadth_exit": SPECS[spec]["breadth_exit"], "insider_asof": st.get("insider_asof"),
           "cash": (book or {}).get("cash"), "nav": nav,
           "holdings": [{"sym": s.split("~")[0], "since": p.get("entry_date"), "entry": p.get("px"),
                         "shares": p.get("sh"), "last": (book.get("last_px") or {}).get(s),
                         "ret_pct": round(((book.get("last_px") or {}).get(s, p["px"]) / p["px"] - 1) * 100, 1)}
                        for s, p in (book.get("pos") or {}).items()],
           "pending_buys": [s.split("~")[0] for s in book.get("pending_buys") or []],
           "pending_sells": [s.split("~")[0] for s in book.get("pending_sells") or []]}
    if nav:
        first, last = nav[0], nav[-1]
        out["since_pct"] = round((last[1] / SPECS[spec]["cfg"].start_cash - 1) * 100, 2)
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
    ap.add_argument("--sleeve", default="multibagger", choices=sorted(SPECS))
    a = ap.parse_args()
    spec = a.sleeve
    if a.status:
        print(json.dumps(snapshot(spec), indent=1, default=str)[:4000])
        return 0
    import multibagger_radar as MR
    st = load_state(spec)
    # the later catch-up slots: the radar already covers the latest session and
    # this sleeve already processed it -> nothing to do, and no rebuild of the
    # whole-market panel (the radar skipped it in this runner)
    try:
        with open(MR.STATE, encoding="utf-8") as f:
            radar_asof = json.load(f).get("asof")
    except (OSError, ValueError):
        radar_asof = None
    if radar_asof and st.get("last_session") and st["last_session"] >= radar_asof:
        print(f"{spec} sleeve already current ({st['last_session']}) — nothing to do")
        return 0
    if not MR.RADAR_PANEL.exists():
        MR.build_recent(date.today())
    from research.grid import load_grid
    g = load_grid(path=MR.RADAR_PANEL)
    before = st.get("last_session")
    st, rows = advance(g, st, spec)
    st["generated"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    save_state(st, spec)
    append_ledger(rows, spec)
    book = st["book"]
    regime = "n/a" if st.get("risk_on") is None else "on" if st["risk_on"] else "OFF"
    feed = f"; promoter disclosures up to {st['insider_asof']}" if st.get("insider_asof") else ""
    print(f"{spec} sleeve: sessions {before or SPECS[spec]['registered']} -> {st.get('last_session')}; "
          f"fills {len(rows)}; holdings {sorted(book['pos'])}; pending buys {book['pending_buys']}; "
          f"cash {book['cash']:,.0f}; regime {regime}{feed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
