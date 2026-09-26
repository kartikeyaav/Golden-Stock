"""
scripts/dashboard_extras.py — the data the v7 interface needs that the classic
payload never carried (2026-09-25).

Every block here answers a question the old dashboard made the reader work out
by hand, and each is computed from files the pipeline already writes:

  setups        every name with a live VCP base, with its pivot, how far price
                sits below it, the volume that would confirm a breakout, and
                the two-lot plan AT THE PIVOT. This is the list the forward
                record says works (alerts with a base beat the universe by
                +13.7% over 40 sessions; alerts without one by +3.7%), and the
                classic page threw the pivots away after the Screener's
                trigger column.
  positions_v7  paper positions with R-now, the next rule that will fire and
                the price it fires at — the position manager's own rules,
                previewed, never applied here. Personal holdings are never
                read (user decision 2026-09-25).
  breadth_hist  % of the watched universe above its own 200-DMA, daily. The
                sizing rule reads this number; the page showed one day of it.
  ew_index      an equal-weight index of the watched universe — the market
                this system actually trades, not the NIFTY 50.
  event_study   forward excess return of every buy alert over the universe at
                fixed horizons, by entry class. The only honest calibration of
                the labels the page asks the reader to act on.
  honest        the 2026-09-25 re-run on the corrected engine (if present).

Display only. Nothing here gates, ranks or sizes a trade.
"""

from __future__ import annotations

import json
import os

import numpy as np
import pandas as pd

from config import RISK, TECHNICAL
from data.cache import load_ohlcv
from scoring.regime import market_risk_scale
from scoring.technical_score import compute_atr, compute_entry_plan

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load_json(*parts):
    p = os.path.join(ROOT, *parts)
    if not os.path.exists(p):
        return None
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def _f(v, nd=2):
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    if x != x or x in (float("inf"), float("-inf")):
        return None
    return round(x, nd)


# ---------------------------------------------------------------------------
# setups: live VCP bases and their pivots
# ---------------------------------------------------------------------------
def build_setups(rows: list[dict]) -> dict:
    ts = _load_json("state", "trigger_state.json") or {}
    trig = ts.get("triggers") or {}
    by_sym = {r["sym"]: r for r in rows}
    scale = market_risk_scale()
    out = []
    for sym, t in trig.items():
        status = (t or {}).get("status") or ""
        if status not in ("AWAITING TRIGGER", "VALIDATED", "VALIDATED (EXTENDED)"):
            continue
        pivot = _f((t or {}).get("pivot"))
        df = load_ohlcv(sym)
        if df is None or len(df) < 60 or not pivot:
            continue
        close = float(df["close"].iloc[-1])
        atr = float(compute_atr(df).iloc[-1])
        avgv = float(df["volume"].tail(50).mean())
        vol_today = float(df["volume"].iloc[-1])
        plan = compute_entry_plan(pivot, atr, risk_scale=scale) if atr > 0 else {"skip": True,
                                                                                  "skip_reason": "no ATR"}
        r = by_sym.get(sym, {})
        out.append({
            "sym": sym, "status": status,
            "company": r.get("company", ""), "ind": r.get("ind", ""), "tier": r.get("tier", ""),
            "tag": r.get("tag", ""), "rs": r.get("rs"), "score": r.get("score"),
            "veto": r.get("veto", False),
            "px": _f(close), "pivot": pivot,
            # positive = price is BELOW the pivot by this much (the move still needed)
            "dist": _f((pivot / close - 1) * 100, 1),
            "zone_top": _f(pivot * 1.05),
            "atr_pct": _f(atr / close * 100, 1),
            "vr": _f(vol_today / avgv, 2) if avgv > 0 else None,
            "vneed": int(avgv * TECHNICAL.breakout_volume_multiple) if avgv > 0 else None,
            "plan": ({"skip": True, "why": str(plan.get("skip_reason", ""))[:140]} if plan.get("skip") else {
                "skip": False, "entry": plan["entry_price"], "stop": plan["stop_loss_price"],
                "shares": plan["shares_total"], "risk": plan["capital_at_risk"],
                "value": plan["position_value"], "partial": plan["partial_profit_price"],
                "be": plan["breakeven_move_trigger_price"],
                "stop_pct": _f((1 - plan["stop_loss_price"] / plan["entry_price"]) * 100, 1)}),
        })
    # nearest to breaking out first; names already through the pivot sit at the top
    out.sort(key=lambda s: (s["status"] == "AWAITING TRIGGER", abs(s["dist"] or 99)))
    return {"date": ts.get("date"), "risk_scale": scale, "rows": out}


# ---------------------------------------------------------------------------
# positions: the next rule that will fire, and where
# ---------------------------------------------------------------------------
def _pos_row(p: dict, source: str) -> dict | None:
    def b(v):
        return str(v).strip().lower() in ("true", "1", "yes")
    t_open, c_open = b(p.get("trading_open")), b(p.get("core_open"))
    if not (t_open or c_open):
        return None
    sym = p.get("symbol")
    df = load_ohlcv(sym)
    if df is None or df.empty:
        return None
    entry = float(p["entry_price"])
    init_stop = float(p["initial_stop"])
    stop = float(p["stop_current"])
    risk = entry - init_stop
    if risk <= 0:
        return None
    close = float(df["close"].iloc[-1])
    low = float(df["low"].iloc[-1])
    sma50 = float(df["close"].rolling(50).mean().iloc[-1]) if len(df) >= 50 else None
    sma150 = float(df["close"].rolling(150).mean().iloc[-1]) if len(df) >= 150 else None
    wk = df.set_index("date")["close"].resample("W-FRI").last().dropna()
    partial_done = b(p.get("partial_taken"))
    be_done = b(p.get("breakeven_moved"))
    shares_t = int(p.get("shares_trading") or 0)
    shares_c = int(p.get("shares_core") or 0)
    partial_sh = int(shares_t * RISK.partial_profit_fraction)
    open_sh = ((shares_t - (partial_sh if partial_done else 0)) if t_open else 0) + (shares_c if c_open else 0)
    r_now = (close - entry) / risk
    partial_px = entry + risk * RISK.partial_profit_r_multiple
    be_px = entry + risk * RISK.breakeven_after_r_multiple

    rules, urgent = [], []
    to_stop = (close / stop - 1) * 100 if stop > 0 else None
    rules.append({"k": "stop", "label": "Stop" + (" (breakeven)" if be_done else ""),
                  "px": _f(stop), "gap": _f(to_stop, 1)})
    if to_stop is not None and to_stop <= 3:
        urgent.append(f"{to_stop:.1f}% above its stop")
    if t_open and not partial_done:
        rules.append({"k": "partial", "label": f"Sell {partial_sh} sh at +{RISK.partial_profit_r_multiple:g}R",
                      "px": _f(partial_px), "gap": _f((partial_px / close - 1) * 100, 1)})
    if not be_done:
        rules.append({"k": "be", "label": f"Stop to breakeven on a close ≥ +{RISK.breakeven_after_r_multiple:g}R",
                      "px": _f(be_px), "gap": _f((be_px / close - 1) * 100, 1)})
    if t_open and partial_done and sma50:
        rules.append({"k": "trail", "label": "Trading lot exits on a close < 50-DMA",
                      "px": _f(sma50), "gap": _f((close / sma50 - 1) * 100, 1)})
        if close < sma50:
            urgent.append("closed below its 50-DMA — the trading lot's exit")
    if c_open and sma150:
        rules.append({"k": "core", "label": "Core lot exits on a weekly close < 30-week MA",
                      "px": _f(sma150), "gap": _f((close / sma150 - 1) * 100, 1)})
        if len(wk) and wk.iloc[-1] < sma150:
            urgent.append("last weekly close below the 30-week MA — the core lot's exit")
    if low <= stop:
        urgent.insert(0, "touched its stop in the last session")
    return {"sym": sym, "source": source, "entry": _f(entry), "entered": str(p.get("entry_date", "")),
            "init_stop": _f(init_stop), "stop": _f(stop), "last": _f(close), "shares": open_sh,
            "r_now": _f(r_now, 2), "pnl_pct": _f((close / entry - 1) * 100, 1),
            "pnl": _f(open_sh * (close - entry), 0), "value": _f(open_sh * close, 0),
            "rules": rules, "urgent": urgent,
            "verdict": str(p.get("verdict") or ""), "conv": str(p.get("conviction") or ""),
            "cohort": str(p.get("cohort") or "")}


def build_positions() -> dict:
    """The PAPER book only.

    PERSONAL HOLDINGS ARE NEVER READ HERE (user decision 2026-09-25: "I don't
    want my holdings to show up"). holdings.csv and positions.csv are not
    opened by any dashboard builder, so refilling them — by hand or through
    import_holdings.py — cannot put a personal position on a page again.
    tests/test_dashboard_v7.py::test_personal_holdings_never_reach_the_page
    pins it."""
    out = {"paper": []}
    path = os.path.join(ROOT, "paper_positions.csv")
    if os.path.exists(path):
        try:
            df = pd.read_csv(path)
        except (OSError, ValueError):
            df = pd.DataFrame()
        for _, p in df.iterrows():
            try:
                r = _pos_row(p.to_dict(), "paper")
            except Exception:  # noqa: BLE001 — one bad row must not blank the page
                r = None
            if r:
                out["paper"].append(r)
    out["paper"].sort(key=lambda r: (not r["urgent"], -(r["r_now"] or 0)))
    return out


# ---------------------------------------------------------------------------
# market: breadth history + equal-weight universe index
# ---------------------------------------------------------------------------
def build_market(symbols: list[str], sessions: int = 260) -> dict:
    above: dict = {}
    count: dict = {}
    rets = []
    for sym in symbols:
        df = load_ohlcv(sym)
        if df is None or len(df) < 60:
            continue
        d = df.tail(sessions + 220).copy()
        d["sma200"] = d["close"].rolling(200).mean()
        tail = d.tail(sessions)
        for dt, c, s in zip(tail["date"], tail["close"], tail["sma200"]):
            if s == s:
                k = str(pd.Timestamp(dt).date())
                count[k] = count.get(k, 0) + 1
                above[k] = above.get(k, 0) + (1 if c > s else 0)
        r = tail.set_index("date")["close"].pct_change(fill_method=None)
        rets.append(r.rename(sym))
    breadth = [[k, round(above[k] / count[k] * 100, 1)] for k in sorted(count) if count[k] >= 100]
    ew = []
    if rets:
        panel = pd.concat(rets, axis=1).sort_index()
        panel = panel.clip(lower=-0.5, upper=1.0)          # a bad print must not move the index
        daily = panel.mean(axis=1, skipna=True).fillna(0.0)
        idx = (1 + daily).cumprod() * 100
        ew = [[str(pd.Timestamp(d).date()), round(float(v), 2)] for d, v in idx.items()]
    return {"breadth": breadth, "ew": ew}


# ---------------------------------------------------------------------------
# the forward record, measured against the universe
# ---------------------------------------------------------------------------
def build_event_study(symbols: list[str]) -> dict:
    """Excess return of each buy alert over the equal-weight universe, from
    the next session's OPEN to the close H sessions later. Fixed horizons, so
    young and old alerts are not mixed; excess over the universe, so a rising
    market does not flatter a label. Same construction as the 2026-09-25
    review (REVIEW_2026-09-25.md)."""
    j_path = os.path.join(ROOT, "journal", "signals_journal.csv")
    e_path = os.path.join(ROOT, "journal", "entry_signals.csv")
    if not os.path.exists(j_path):
        return {}
    j = pd.read_csv(j_path, parse_dates=["logged_at"])
    from config import BUY_ALERT_KINDS
    j = j[j["kind"].isin(BUY_ALERT_KINDS)].copy()
    if j.empty:
        return {}
    es = pd.read_csv(e_path, parse_dates=["logged_at"]) if os.path.exists(e_path) else pd.DataFrame()
    status = {}
    if not es.empty:
        for _, r in es.iterrows():
            status[(r["symbol"], str(r["logged_at"])[:10], r["kind"])] = r.get("entry_status")
    start = j["logged_at"].min() - pd.Timedelta(days=5)
    closes, opens = {}, {}
    for s in symbols:
        df = load_ohlcv(s)
        if df is None or df.empty:
            continue
        d = df[df["date"] >= start]
        closes[s] = d.set_index("date")["close"]
        opens[s] = d.set_index("date")["open"]
    C = pd.DataFrame(closes).sort_index()
    O = pd.DataFrame(opens).sort_index()
    if C.empty:
        return {}
    dates = C.index
    H = (10, 20, 40)
    rows = []
    for _, r in j.iterrows():
        s = r["symbol"]
        if s not in C.columns:
            continue
        after = dates[dates > pd.Timestamp(r["logged_at"].date())]
        if not len(after):
            continue
        d0 = after[0]
        i0 = dates.get_loc(d0)
        e = O.at[d0, s]
        if not (e == e and e > 0):
            continue
        st = status.get((s, str(r["logged_at"])[:10], r["kind"])) or "UNLABELLED"
        if r["kind"] == "EPISODIC PIVOT":
            st = "EP EVENT"
        rec = {"status": st, "kind": r["kind"], "conv": r.get("conviction_score")}
        for h in H:
            if i0 + h - 1 < len(dates):
                d1 = dates[i0 + h - 1]
                x = C.at[d1, s] / e - 1
                u = (C.loc[d1] / O.loc[d0] - 1)
                u = u[(u > -0.9) & (u < 5)].mean()
                if x == x and u == u:
                    rec[h] = (x - u) * 100
        rows.append(rec)
    E = pd.DataFrame(rows)
    if E.empty:
        return {}

    def agg(g):
        out = {"n": int(len(g))}
        for h in H:
            x = g[h].dropna() if h in g else pd.Series(dtype=float)
            out[f"n{h}"] = int(len(x))
            out[f"x{h}"] = _f(x.mean(), 2) if len(x) else None
            out[f"b{h}"] = _f((x > 0).mean() * 100, 0) if len(x) else None
        return out

    label = {"VALIDATED": "Breakout trigger fired", "EP EVENT": "Episodic pivot (gap)",
             "AWAITING TRIGGER": "Base ready, pivot not yet broken",
             "NO VCP BASE": "Uptrend only, no base", "VALIDATED (EXTENDED)": "Trigger on an extended chart",
             "UNLABELLED": "Before labels existed"}
    by_status = [{"cohort": label.get(k, k), "key": k, **agg(g)} for k, g in E.groupby("status")]
    order = ["VALIDATED", "EP EVENT", "AWAITING TRIGGER", "NO VCP BASE", "VALIDATED (EXTENDED)", "UNLABELLED"]
    by_status.sort(key=lambda r: order.index(r["key"]) if r["key"] in order else 99)
    conv = pd.to_numeric(E["conv"], errors="coerce")
    by_conv = []
    for lo, hi, name in ((0, 50, "under 50"), (50, 60, "50–60"), (60, 70, "60–70"), (70, 101, "70+")):
        g = E[(conv >= lo) & (conv < hi)]
        if len(g):
            by_conv.append({"cohort": name, **agg(g)})
    return {"horizons": list(H), "by_status": by_status, "by_conv": by_conv, "all": agg(E),
            "as_of": str(dates[-1].date())}


# ---------------------------------------------------------------------------
# the 2026-09-25 honest re-run (committed, static)
# ---------------------------------------------------------------------------
def build_honest() -> dict | None:
    res = _load_json("honest_rerun_results.json")
    if not res:
        return None
    curves = _load_json("honest_rerun_curves.json")
    return {"rows": res, "curves": curves}


def build_deals(symbols: list[str]) -> dict | None:
    """Bulk and block deals on watched names (data/deals.py): the recent
    NAMED deals (same-session buy+sell churn set aside) and a 90-day net per
    symbol for the stock page. Context only."""
    from data import deals
    df = deals.load()
    if df.empty:
        return None
    watched = set(symbols)
    df = df[df["symbol"].isin(watched)]
    flagged = deals.with_churn_flag(df)
    since30 = (pd.Timestamp.now() - pd.Timedelta(days=30)).strftime("%Y-%m-%d")
    since90 = (pd.Timestamp.now() - pd.Timedelta(days=90)).strftime("%Y-%m-%d")
    named = flagged[(~flagged["churn"]) & (flagged["date"] >= since30)].copy()
    named["value"] = named["qty"] * named["price"]
    named = named[named["value"] >= 1e7].sort_values(["date", "value"], ascending=[False, False])
    recent = [{"d": r.date, "sym": r.symbol, "client": str(r.client)[:60], "side": r.side,
               "qty": int(r.qty), "price": _f(r.price), "value": _f(r.value, 0), "kind": r.kind}
              for r in named.head(150).itertuples()]
    per = {}
    for r in deals.net_by_symbol(df, since90).itertuples():
        per[r.symbol] = {"net": _f(r.net_value, 0), "buy": _f(r.buy_value, 0),
                         "sell": _f(r.sell_value, 0), "buyers": list(r.buyers)[:3], "n": int(r.deals)}
    rows90 = flagged[(~flagged["churn"]) & (flagged["date"] >= since90)]
    by_sym = {}
    for r in rows90.itertuples():
        by_sym.setdefault(r.symbol, []).append(
            {"d": r.date, "client": str(r.client)[:60], "side": r.side, "qty": int(r.qty),
             "price": _f(r.price), "kind": r.kind})
    first = str(df["date"].min()) if len(df) else None
    churn_share = round(float(flagged["churn"].mean() * 100), 0) if len(flagged) else None
    return {"since": first, "churn_pct": churn_share, "recent": recent, "net90": per, "rows90": by_sym}


def build_momentum() -> dict | None:
    """The momentum-core paper sleeve (PREREG_2026-09-25_momentum_core.md):
    the recorded rebalances and NAV, tonight's holdings, the preview of the
    next rebalance, and the forward comparison it is judged by."""
    import momentum_core
    st = momentum_core.snapshot()
    st.pop("capital", None)
    return st


def build_multibagger_sleeve() -> dict | None:
    """The multibagger sleeve (PREREG_2026-09-27_multibagger_sleeve.md):
    holdings, pending orders, NAV and the MIDSMALL comparison."""
    import multibagger_sleeve
    return multibagger_sleeve.snapshot()


def build_all(payload: dict) -> dict:
    rows = payload.get("rows") or []
    syms = [r["sym"] for r in rows]
    extras = {}
    for key, fn in (("setups", lambda: build_setups(rows)),
                    ("positions_v7", build_positions),
                    ("market", lambda: build_market(syms)),
                    ("event_study", lambda: build_event_study(syms)),
                    ("honest", build_honest),
                    ("momentum", build_momentum),
                    ("radar", lambda: _load_json("state", "multibagger_radar.json")),
                    ("mbsleeve", build_multibagger_sleeve),
                    ("deals", lambda: build_deals(syms)),
                    ("macro", lambda: _load_json("state", "macro_radar.json"))):
        try:
            extras[key] = fn()
        except Exception as exc:  # noqa: BLE001 — an extra must never kill the build
            extras[key] = None
            print(f"dashboard extra '{key}' degraded: {exc}")
    return extras
