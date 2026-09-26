"""
scripts/momentum_core.py — the momentum core, run forward as a PAPER sleeve
(PREREG_2026-09-25_momentum_core.md). Runs after the nightly scan.

Each run:
  1. builds price panels for the frozen index universe from the cache
  2. if a calendar month has closed since the last rebalance, and the first
     session after it has traded, rebalances AT THAT SESSION'S OPEN from the
     scores at the month's last close (the registered timing) and appends
     every fill to journal/momentum_core_ledger.csv
  3. rebuilds the NAV series from the recorded rebalances — holdings only
     change at a rebalance, so NAV on any day is cash + shares x close, and a
     night the job did not run leaves no hole
  4. writes a PREVIEW: the list the rules would pick if the month ended at
     tonight's close, so the next rebalance is never a surprise

Idempotent: a rebalance is keyed by its signal date and executes once. The
cloud is the only writer of state/momentum_core.json (daily.yml commits it);
the local Run panel does not run this, so the two machines never race on it.

    python scripts/momentum_core.py            # nightly
    python scripts/momentum_core.py --status   # print the sleeve, change nothing
"""

from __future__ import annotations

import csv
import json
import os
import sys
from datetime import datetime

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.cache import list_cached, load_ohlcv
from scoring import momentum

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE = os.path.join(ROOT, "state", "momentum_core.json")
LEDGER = os.path.join(ROOT, "journal", "momentum_core_ledger.csv")
LEDGER_FIELDS = ["date", "signal", "symbol", "action", "shares", "price", "value", "cost", "reason"]

REGISTERED = "2026-09-25"          # the first month-end on or after this date is the first signal
CAPITAL = 1_000_000.0
COST_PCT = 0.25                    # per side, registered
INDEX_SOURCES = ("smallcap250", "midcap150", "microcap250")
MIN_BARS = 65


def universe() -> list[str]:
    u = pd.read_csv(os.path.join(ROOT, "universe.csv"))
    return u.loc[u["index_source"].isin(INDEX_SOURCES), "symbol"].astype(str).tolist()


def load_panels(symbols: list[str]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    cached = set(list_cached())
    close, opn, vol = {}, {}, {}
    for s in symbols:
        if s not in cached:
            continue
        df = load_ohlcv(s)
        if df is None or len(df) < MIN_BARS:
            continue
        d = df.set_index("date")
        close[s], opn[s], vol[s] = d["close"], d["open"], d["volume"]
    C = pd.DataFrame(close).sort_index()
    return C, pd.DataFrame(opn).reindex(C.index), pd.DataFrame(vol).reindex(C.index)


def exposure_for(breadth: float | None) -> float:
    """The registered breadth rule. An UNKNOWN breadth (too few names with
    enough history to measure it) is defensive, never full — missing data must
    not buy the sleeve its maximum exposure."""
    if breadth is None:
        return 0.5
    return 0.5 if breadth < 50 else 1.0


def month_end_signals(dates: pd.DatetimeIndex) -> list[pd.Timestamp]:
    """Last session of every calendar month that has CLOSED — i.e. a later
    month already has a session in the data."""
    s = pd.Series(dates, index=dates)
    ends = s.groupby(dates.to_period("M")).last()
    last_period = dates[-1].to_period("M")
    return [pd.Timestamp(d) for p, d in ends.items() if p < last_period]


def load_state() -> dict:
    if os.path.exists(STATE):
        try:
            with open(STATE, encoding="utf-8") as f:
                return json.load(f)
        except (OSError, ValueError):
            pass
    return {"registered": REGISTERED, "capital": CAPITAL, "cost_pct": COST_PCT,
            "rebalances": [], "nav": [], "preview": None}


def save_state(st: dict) -> None:
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    tmp = STATE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(st, f, indent=1, default=str)
    os.replace(tmp, STATE)


def append_ledger(rows: list[dict]) -> None:
    if not rows:
        return
    new = not os.path.exists(LEDGER)
    os.makedirs(os.path.dirname(LEDGER), exist_ok=True)
    with open(LEDGER, "a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=LEDGER_FIELDS)
        if new:
            w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in LEDGER_FIELDS})


def current_book(st: dict) -> tuple[dict, float]:
    if st["rebalances"]:
        last = st["rebalances"][-1]
        return dict(last["holdings_after"]), float(last["cash_after"])
    return {}, float(st.get("capital", CAPITAL))


def rebuild_nav(st: dict, C: pd.DataFrame) -> list[list]:
    """NAV for every session from the first fill, from the recorded books."""
    if not st["rebalances"]:
        return []
    first = pd.Timestamp(st["rebalances"][0]["fill"])
    dates = C.index[C.index >= first]
    last_px = C.ffill()
    out, k = [], 0
    rebs = st["rebalances"]
    for d in dates:
        while k + 1 < len(rebs) and pd.Timestamp(rebs[k + 1]["fill"]) <= d:
            k += 1
        book = rebs[k]
        val = float(book["cash_after"]) + sum(
            float(sh) * float(last_px.at[d, s]) for s, sh in book["holdings_after"].items()
            if s in last_px.columns and pd.notna(last_px.at[d, s]))
        out.append([str(d.date()), round(val, 2)])
    return out


def run(dry: bool = False) -> dict:
    st = load_state()
    C, O, V = load_panels(universe())
    if C.empty:
        print("momentum core: no prices — nothing to do")
        return st
    pp = momentum.panels(C, C * V)
    dates = C.index
    signals = [s for s in month_end_signals(dates) if s >= pd.Timestamp(st.get("registered", REGISTERED))]
    done = {r["signal"] for r in st["rebalances"]}
    last_px = {}
    new_rows = []
    for sig in signals:
        key = str(sig.date())
        if key in done:
            continue
        after = dates[dates > sig]
        if not len(after):
            continue                              # the fill session has not traded yet
        fill = after[0]
        holdings, cash = current_book(st)
        for s, p in C.loc[:sig].ffill().iloc[-1].items():
            if pd.notna(p) and p > 0:
                last_px[s] = float(p)
        ranked = momentum.score_at(pp, sig)
        if ranked.empty:
            print(f"momentum core: too few eligible names on {key} — rebalance skipped")
            continue
        targets = momentum.target_names(ranked, holdings)
        breadth = momentum.breadth_at(C, sig)
        exposure = exposure_for(breadth)
        target_w = {s: exposure / len(targets) for s in targets}
        fills: list = []
        before = set(holdings)
        holdings, cash, traded = momentum.rebalance(holdings, cash, target_w, O.loc[fill],
                                                    last_px, COST_PCT, fills)
        rank = {s: i + 1 for i, s in enumerate(ranked.index)}
        for f in fills:
            f.update({"date": str(fill.date()), "signal": key,
                      "reason": f"rank {rank.get(f['symbol'], '—')} of {len(ranked)}; exposure {exposure:.0%}"})
        new_rows += fills
        st["rebalances"].append({
            "signal": key, "fill": str(fill.date()), "exposure": exposure,
            "breadth": round(breadth, 1) if breadth is not None else None,
            "targets": targets, "added": sorted(set(targets) - before), "dropped": sorted(before - set(targets)),
            "traded_value": round(traded, 2), "cash_after": round(cash, 2),
            "holdings_after": {s: round(float(sh), 6) for s, sh in holdings.items()},
        })
        done.add(key)
        print(f"momentum core: REBALANCED for signal {key} at the {fill.date()} open — "
              f"{len(targets)} names, exposure {exposure:.0%}, "
              f"+{len(set(targets) - before)} / -{len(before - set(targets))}")

    finish(st, C, pp)
    if not dry:
        append_ledger(new_rows)
        save_state(st)
    return st


def finish(st: dict, C: pd.DataFrame, pp: dict) -> None:
    """NAV from the recorded books, and the preview of the next rebalance."""
    st["nav"] = rebuild_nav(st, C)
    latest = C.index[-1]
    holdings, cash = current_book(st)
    ranked = momentum.score_at(pp, latest)
    prev_targets = momentum.target_names(ranked, holdings) if not ranked.empty else []
    breadth = momentum.breadth_at(C, latest)
    rank = {s: i + 1 for i, s in enumerate(ranked.index)}
    r6 = pp["r6"].loc[latest]
    r12 = pp["r12"].loc[latest]
    vol = pp["vol1y"].loc[latest]
    st["preview"] = {
        "asof": str(latest.date()),
        "exposure": exposure_for(breadth),
        "breadth": round(breadth, 1) if breadth is not None else None,
        "eligible": int(len(ranked)),
        "targets": [{"sym": s, "rank": rank.get(s), "score": round(float(ranked.get(s, float("nan"))), 3),
                     "r6": round(float(r6.get(s)) * 100, 1) if pd.notna(r6.get(s)) else None,
                     "r12": round(float(r12.get(s)) * 100, 1) if pd.notna(r12.get(s)) else None,
                     "vol": round(float(vol.get(s)) * 100, 1) if pd.notna(vol.get(s)) else None,
                     "held": s in holdings,
                     "close": round(float(C[s].dropna().iloc[-1]), 2) if s in C.columns else None}
                    for s in prev_targets],
        "adds": sorted(set(prev_targets) - set(holdings)),
        "drops": sorted(set(holdings) - set(prev_targets)),
    }
    st["updated"] = datetime.now().strftime("%Y-%m-%d %H:%M")


def snapshot() -> dict:
    """What the dashboard shows: the RECORDED sleeve (no pending rebalance is
    executed here, not even in memory — a display must never show a trade the
    ledger does not have), its NAV marked to tonight's closes, the next
    rebalance preview, and the forward comparison the pre-registration judges
    it by (the frozen universe equal-weight, the MIDSMALL ETF, the NIFTY 50)."""
    st = load_state()
    C, O, V = load_panels(universe())
    if C.empty:
        return st
    finish(st, C, momentum.panels(C, C * V))
    nav = st.get("nav") or []
    if nav:
        start = pd.Timestamp(nav[0][0])
        rets = C[C.index >= start].pct_change(fill_method=None).clip(-0.5, 1.0)
        ew = (1 + rets.mean(axis=1, skipna=True).fillna(0)).cumprod()
        cmp = {"sleeve": round((nav[-1][1] / nav[0][1] - 1) * 100, 2),
               "universe_ew": round((float(ew.iloc[-1]) - 1) * 100, 2)}
        for key, sym in (("midsmall", "MIDSMALL"), ("nifty", "NIFTY50")):
            b = load_ohlcv(sym)
            if b is not None and len(b):
                b = b.set_index("date")["close"]
                b = b[b.index >= start]
                if len(b) > 1:
                    cmp[key] = round((float(b.iloc[-1]) / float(b.iloc[0]) - 1) * 100, 2)
        st["compare"] = cmp
    # holdings marked to tonight: weight, and return since the name entered
    holdings, cash = current_book(st)
    entry_px = {}
    if os.path.exists(LEDGER):
        try:
            led = pd.read_csv(LEDGER)
            for _, r in led[led["action"] == "BUY"].iterrows():
                entry_px[str(r["symbol"])] = (str(r["date"]), float(r["price"]))
        except (OSError, ValueError, KeyError):
            pass
    last = C.ffill().iloc[-1]
    rows = []
    total = cash + sum(float(sh) * float(last.get(s, 0) or 0) for s, sh in holdings.items())
    for s, sh in holdings.items():
        px = float(last.get(s, 0) or 0)
        d, e = entry_px.get(s, ("", None))
        rows.append({"sym": s, "shares": round(float(sh), 3), "close": round(px, 2),
                     "value": round(float(sh) * px, 2), "weight": round(float(sh) * px / total * 100, 1) if total else None,
                     "since": d, "ret": round((px / e - 1) * 100, 1) if e else None})
    rows.sort(key=lambda r: -(r["value"] or 0))
    st["book"] = {"cash": round(cash, 2), "total": round(total, 2), "rows": rows}
    return st


def main() -> None:
    if "--status" in sys.argv:
        st = load_state()
        nav = st.get("nav") or []
        print(f"momentum core: {len(st.get('rebalances', []))} rebalances; "
              f"NAV {nav[-1][1]:,.0f} on {nav[-1][0]}" if nav else "momentum core: no rebalance yet")
        return
    st = run()
    nav = st.get("nav") or []
    pv = st.get("preview") or {}
    print(f"momentum core: {len(st['rebalances'])} rebalance(s); "
          + (f"NAV ₹{nav[-1][1]:,.0f} on {nav[-1][0]}; " if nav else "holding cash until the first month-end; ")
          + f"preview {len(pv.get('targets', []))} names as of {pv.get('asof')}")


if __name__ == "__main__":
    main()
