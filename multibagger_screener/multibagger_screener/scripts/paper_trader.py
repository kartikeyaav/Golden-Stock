"""
scripts/paper_trader.py — the analyst's paper book: every analyst BUY verdict
becomes a simulated position, managed by the SAME two-lot rules as real
positions, so "did the analyst layer add money?" gets a number instead of an
opinion. This is the forward test of the AI layer (HANDOFF section 3: the AI
is on probation until the journal proves it).

Rules (all mechanical, no discretion):
  ENTRY   first session OPEN strictly after the verdict date (honest fill —
          verdicts land post-close; next-open execution was stress-validated
          at +0.96R). Gap below the suggested stop at the open = no trade.
  STOP    the alert card's suggested stop (2.5xATR at signal time).
  SIZE    RISK.capital x RISK.risk_per_trade_pct x regime scale, halved when
          the verdict says HALF PLAN; position value capped at 15% of book.
  EXITS   scripts/position_manager.check_positions on paper_positions.csv —
          identical stop/partial/breakeven/50-DMA/30-week-MA logic, fills
          booked to journal/paper_ledger.csv.

State: paper_positions.csv (positions.csv schema + verdict columns).
Idempotent: each verdict is keyed symbol@verdict-timestamp; skips are
recorded in the ledger so they don't retry forever. Runs nightly from
daily_job (after the analyst, before the dashboard).

    python scripts/paper_trader.py            # fill new verdicts + manage book
    python scripts/paper_trader.py --summary  # just print the scorecard
"""

from __future__ import annotations

import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import RISK
from data.cache import load_ohlcv
from scoring.regime import market_risk_scale
from position_manager import check_positions, append_ledger

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAPER_PATH = os.path.join(ROOT, "paper_positions.csv")
LEDGER_PATH = os.path.join(ROOT, "journal", "paper_ledger.csv")
VERDICTS_PATH = os.path.join(ROOT, "journal", "analyst_verdicts.csv")
SIGNALS_PATH = os.path.join(ROOT, "journal", "signals_journal.csv")
ALERTS_PATH = os.path.join(ROOT, "daily_alerts.md")

PAPER_COLUMNS = ["symbol", "entry_date", "entry_price", "initial_stop",
                 "stop_current", "shares_trading", "shares_core",
                 "trading_open", "core_open", "partial_taken",
                 "breakeven_moved", "notes",
                 "verdict_id", "verdict", "conviction", "size_plan"]


def _load_paper() -> pd.DataFrame:
    if os.path.exists(PAPER_PATH):
        return pd.read_csv(PAPER_PATH)
    return pd.DataFrame(columns=PAPER_COLUMNS)


def _handled_verdict_ids() -> set[str]:
    """Verdicts already turned into a position OR already skipped for cause."""
    ids = set()
    pos = _load_paper()
    if not pos.empty and "verdict_id" in pos.columns:
        ids |= set(pos["verdict_id"].dropna().astype(str))
    if os.path.exists(LEDGER_PATH):
        led = pd.read_csv(LEDGER_PATH)
        skips = led[led["action"] == "SKIP"]
        ids |= set(skips["reason"].str.extract(r"\[(.+?)\]")[0].dropna())
    return ids


def _signal_for(verdicts_row, signals: pd.DataFrame):
    """The alert that triggered this verdict: latest buy-type journal row for
    the symbol at or before the verdict, within 5 days."""
    sym = verdicts_row["symbol"]
    vts = pd.Timestamp(verdicts_row["logged_at"])
    cand = signals[(signals["symbol"] == sym)
                   & (signals["kind"].isin(["BUY CANDIDATE", "RE-ENTRY WINDOW"]))
                   & (signals["logged_at"] <= vts)
                   & (signals["logged_at"] >= vts - pd.Timedelta(days=5))]
    return cand.iloc[-1] if len(cand) else None


def open_from_verdicts() -> list[str]:
    """Turn unhandled analyst BUY verdicts into paper positions. Verdicts
    whose next session hasn't traded yet stay pending (picked up tomorrow)."""
    if not os.path.exists(VERDICTS_PATH):
        return []
    verdicts = pd.read_csv(VERDICTS_PATH, parse_dates=["logged_at"])
    buys = verdicts[verdicts["verdict"].str.upper() == "BUY"]
    if buys.empty:
        return []
    signals = pd.read_csv(SIGNALS_PATH, parse_dates=["logged_at"]) \
        if os.path.exists(SIGNALS_PATH) else pd.DataFrame()
    handled = _handled_verdict_ids()
    pos = _load_paper()
    lines, skip_rows, new_rows = [], [], []

    def skip(vid, sym, why):
        skip_rows.append({"date": str(pd.Timestamp.now().date()), "symbol": sym,
                          "action": "SKIP", "lot": "entry", "shares": 0,
                          "price": "", "pnl": "", "reason": f"[{vid}] {why}"})
        lines.append(f"- PAPER SKIP {sym}: {why}")

    for _, v in buys.iterrows():
        vid = f"{v['symbol']}@{v['logged_at']:%Y-%m-%d %H:%M}"
        if vid in handled:
            continue
        sym = v["symbol"]
        # one open paper position per symbol — no pyramiding in the paper book
        if not pos.empty and ((pos["symbol"] == sym)
                              & (pos["trading_open"].astype(str).str.lower().isin(["true", "1"])
                                 | pos["core_open"].astype(str).str.lower().isin(["true", "1"]))).any():
            skip(vid, sym, "already open in paper book")
            continue
        sig = _signal_for(v, signals) if not signals.empty else None
        if sig is None:
            skip(vid, sym, "no matching alert in signals journal")
            continue
        stop = pd.to_numeric(pd.Series([sig.get("stop_suggested")]), errors="coerce").iloc[0]
        if pd.isna(stop):
            skip(vid, sym, "alert had no mechanical stop (risk engine skipped the plan)")
            continue
        df = load_ohlcv(sym)
        if df is None or df.empty:
            skip(vid, sym, "no price data")
            continue
        after = df[df["date"] > pd.Timestamp(v["logged_at"]).normalize()]
        if after.empty:
            lines.append(f"- PAPER PENDING {sym}: fills at next session's open")
            continue  # NOT marked handled — retried next run
        fill_bar = after.iloc[0]
        entry = float(fill_bar["open"])
        stop = float(stop)
        if entry <= stop:
            skip(vid, sym, f"gapped below stop at open ({entry:.2f} <= {stop:.2f})")
            continue
        size_plan = str(v.get("size", "") or "")
        scale = market_risk_scale() * (0.5 if "HALF" in size_plan.upper() else 1.0)
        risk_amount = RISK.capital * RISK.risk_per_trade_pct / 100.0 * scale
        shares = int(risk_amount / (entry - stop))
        shares = min(shares, int(RISK.capital * RISK.max_position_value_pct / 100.0 / entry))
        if shares < 2:
            skip(vid, sym, "stop too wide to size (<2 shares at risk budget)")
            continue
        trading = shares // 2
        core = shares - trading
        new_rows.append({
            "symbol": sym, "entry_date": str(pd.Timestamp(fill_bar["date"]).date()),
            "entry_price": round(entry, 2), "initial_stop": round(stop, 2),
            "stop_current": round(stop, 2), "shares_trading": trading,
            "shares_core": core, "trading_open": True, "core_open": True,
            "partial_taken": False, "breakeven_moved": False,
            "notes": f"PAPER auto-entry from analyst verdict {v['logged_at']:%Y-%m-%d}",
            "verdict_id": vid, "verdict": v["verdict"],
            "conviction": v.get("conviction", ""), "size_plan": size_plan,
        })
        skip_rows.append({"date": str(pd.Timestamp(fill_bar["date"]).date()),
                          "symbol": sym, "action": "BUY", "lot": "entry",
                          "shares": shares, "price": round(entry, 2), "pnl": "",
                          "reason": f"[{vid}] analyst {v['verdict']}/"
                                    f"{v.get('conviction', '')}/{size_plan}"})
        lines.append(f"- PAPER BUY {sym}: {shares} sh @ {entry:.2f} "
                     f"(stop {stop:.2f}, {size_plan or 'FULL PLAN'})")

    if new_rows:
        add = pd.DataFrame(new_rows)
        pos = add if pos.empty else pd.concat([pos, add], ignore_index=True)
        pos.to_csv(PAPER_PATH, index=False)
    append_ledger(LEDGER_PATH, skip_rows)
    return lines


def summarize() -> dict:
    """Dashboard/CLI scorecard: open positions marked to market, realized
    P&L from the ledger, pending verdicts awaiting their fill bar."""
    out = {"equity": RISK.capital, "realized": 0.0, "unrealized": 0.0,
           "open": [], "pending": [], "ledger": [], "n_closed": 0}
    led = pd.read_csv(LEDGER_PATH) if os.path.exists(LEDGER_PATH) else pd.DataFrame()
    if not led.empty:
        out["realized"] = float(pd.to_numeric(led[led["action"] == "SELL"]["pnl"],
                                              errors="coerce").sum())
        out["ledger"] = [{"d": r["date"], "sym": r["symbol"], "action": r["action"],
                          "lot": r["lot"], "shares": r["shares"],
                          "price": r["price"] if pd.notna(r["price"]) else "",
                          "pnl": r["pnl"] if pd.notna(r["pnl"]) else "",
                          "reason": str(r["reason"])}
                         for _, r in led.tail(20).iloc[::-1].iterrows()]
    pos = _load_paper()

    def _b(v):
        return str(v).strip().lower() in ("true", "1", "yes")

    for _, p in pos.iterrows():
        t_open, c_open = _b(p["trading_open"]), _b(p["core_open"])
        if not (t_open or c_open):
            out["n_closed"] += 1
            continue
        df = load_ohlcv(p["symbol"])
        last = float(df["close"].iloc[-1]) if df is not None and len(df) else float(p["entry_price"])
        partial = int(int(p["shares_trading"]) * RISK.partial_profit_fraction) \
            if _b(p["partial_taken"]) else 0
        open_sh = ((int(p["shares_trading"]) - partial) if t_open else 0) \
            + (int(p["shares_core"]) if c_open else 0)
        entry = float(p["entry_price"])
        upnl = open_sh * (last - entry)
        out["unrealized"] += upnl
        out["open"].append({
            "sym": p["symbol"], "entered": str(p["entry_date"]),
            "entry": entry, "stop": float(p["stop_current"]), "last": round(last, 2),
            "shares": open_sh, "pnl": round(upnl, 2),
            "pnl_pct": round((last / entry - 1) * 100, 2),
            "verdict": f"{p.get('verdict', '')}/{p.get('conviction', '')}"
                       f"/{p.get('size_plan', '')}".strip("/"),
        })

    # pending = BUY verdicts not yet handled (no position, no skip)
    if os.path.exists(VERDICTS_PATH):
        verdicts = pd.read_csv(VERDICTS_PATH, parse_dates=["logged_at"])
        handled = _handled_verdict_ids()
        for _, v in verdicts[verdicts["verdict"].str.upper() == "BUY"].iterrows():
            vid = f"{v['symbol']}@{v['logged_at']:%Y-%m-%d %H:%M}"
            if vid not in handled:
                out["pending"].append({"sym": v["symbol"],
                                       "verdict": f"BUY/{v.get('conviction', '')}"
                                                  f"/{v.get('size', '')}",
                                       "d": f"{v['logged_at']:%Y-%m-%d}"})
    out["net"] = round(out["realized"] + out["unrealized"], 2)
    out["net_pct"] = round(out["net"] / RISK.capital * 100, 3)
    out["realized"] = round(out["realized"], 2)
    out["unrealized"] = round(out["unrealized"], 2)
    return out


def main() -> None:
    if "--summary" not in sys.argv:
        lines = open_from_verdicts()
        alerts, _ = check_positions(PAPER_PATH, ledger_path=LEDGER_PATH, label="PAPER")
        lines += alerts
        if lines and os.path.exists(ALERTS_PATH):
            with open(ALERTS_PATH, "a", encoding="utf-8") as f:
                f.write("\n## Paper book (analyst-driven)\n\n" + "\n".join(lines) + "\n")
        for ln in lines:
            print(ln)
    s = summarize()
    print(f"paper book: {len(s['open'])} open, {s['n_closed']} closed, "
          f"{len(s['pending'])} pending | realized {s['realized']:+,.0f} "
          f"unrealized {s['unrealized']:+,.0f} | NET {s['net']:+,.0f} INR "
          f"({s['net_pct']:+.2f}% of {RISK.capital:,.0f})")


if __name__ == "__main__":
    main()
