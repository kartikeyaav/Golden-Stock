"""
scripts/position_manager.py — trade the plan you were given.

The system hands out two-lot plans at entry; this module tracks each open
position in positions.csv against ITS OWN plan every scan and alerts on:

  STOP HIT          day's low touched the current stop -> exit everything open
  PARTIAL PROFIT    +2.5R touched -> sell 1/3 of the trading lot (once)
  MOVE TO BREAKEVEN +1.5R closed -> stops ratchet to entry (once)
  TRADING LOT EXIT  after partial: daily close below the 50-DMA
  CORE LOT EXIT     Friday close below the 150-day SMA (~30-week MA)

State flags (partial_taken, breakeven_moved, lot open/closed) are persisted
back into positions.csv so each event fires exactly once. Execution stays
HUMAN — these are instructions, not orders (brief: no auto-execution).

The same rules also manage the PAPER book (scripts/paper_trader.py):
check_positions takes a positions_path so real and paper positions share ONE
implementation of the exit logic, and an optional ledger_path — when given,
every exit event also books a fill row (date, action, lot, shares, price,
pnl) so net gain is computable.

positions.csv columns: symbol, entry_date, entry_price, initial_stop,
stop_current, shares_trading, shares_core, trading_open, core_open,
partial_taken, breakeven_moved, notes  (extra columns are preserved)
"""

from __future__ import annotations

import csv
import os

import pandas as pd

from config import RISK
from data.cache import load_ohlcv
from scoring.technical_score import add_moving_averages

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POSITIONS_PATH = os.path.join(ROOT, "positions.csv")

LEDGER_FIELDS = ["date", "symbol", "action", "lot", "shares", "price", "pnl", "reason"]


def _bool(v) -> bool:
    return str(v).strip().lower() in ("true", "1", "yes")


def append_ledger(ledger_path: str, rows: list[dict]) -> None:
    if not rows:
        return
    os.makedirs(os.path.dirname(ledger_path), exist_ok=True)
    new_file = not os.path.exists(ledger_path)
    with open(ledger_path, "a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=LEDGER_FIELDS)
        if new_file:
            w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in LEDGER_FIELDS})


def check_positions(positions_path: str = POSITIONS_PATH,
                    ledger_path: str | None = None,
                    label: str = "POSITION") -> tuple[list[str], list[dict]]:
    """Returns (alert_lines, journal_rows) and persists updated flags."""
    if not os.path.exists(positions_path):
        return [], []
    pos = pd.read_csv(positions_path)
    if pos.empty:
        return [], []

    alerts: list[str] = []
    journal_rows: list[dict] = []
    ledger_rows: list[dict] = []
    now = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M")

    for i, p in pos.iterrows():
        trading_open, core_open = _bool(p["trading_open"]), _bool(p["core_open"])
        if not (trading_open or core_open):
            continue
        df = load_ohlcv(p["symbol"])
        if df is None or df.empty:
            continue
        df = add_moving_averages(df)
        row = df.iloc[-1]
        entry, stop = float(p["entry_price"]), float(p["stop_current"])
        risk = entry - float(p["initial_stop"])
        if risk <= 0:
            continue
        shares_trading = int(p["shares_trading"])
        partial_shares = int(shares_trading * RISK.partial_profit_fraction)

        def fire(msg: str):
            alerts.append(f"- **{label}**: {p['symbol']} — {msg}")
            journal_rows.append({"logged_at": now, "symbol": p["symbol"],
                                 "kind": "MANAGE", "new_tag": msg[:60],
                                 "close": float(row["close"])})

        def book(lot: str, shares: int, price: float, reason: str, when=None):
            if ledger_path and shares > 0:
                ledger_rows.append({
                    "date": str(pd.Timestamp(when if when is not None else row["date"]).date()),
                    "symbol": p["symbol"], "action": "SELL", "lot": lot,
                    "shares": shares, "price": round(float(price), 2),
                    "pnl": round(shares * (float(price) - entry), 2),
                    "reason": reason})

        # 1. stop hit -> everything open exits
        if row["low"] <= stop:
            fire(f"STOP HIT at {stop:.2f} (low {row['low']:.2f}) — exit all remaining shares")
            open_shares = ((shares_trading - (partial_shares if _bool(p["partial_taken"]) else 0))
                           if trading_open else 0) + (int(p["shares_core"]) if core_open else 0)
            book("all", open_shares, stop, "stop hit")
            pos.at[i, "trading_open"] = False
            pos.at[i, "core_open"] = False
            continue

        # 2. partial profit (trading lot, once)
        partial_level = entry + risk * RISK.partial_profit_r_multiple
        if trading_open and not _bool(p["partial_taken"]) and row["high"] >= partial_level:
            fire(f"PARTIAL PROFIT {RISK.partial_profit_r_multiple}R hit at "
                 f"{partial_level:.2f} — sell ~{partial_shares} sh of trading lot")
            book("partial", partial_shares, partial_level,
                 f"partial at {RISK.partial_profit_r_multiple}R")
            pos.at[i, "partial_taken"] = True

        # 3. breakeven ratchet (both lots, once)
        be_trigger = entry + risk * RISK.breakeven_after_r_multiple
        if not _bool(p["breakeven_moved"]) and row["close"] >= be_trigger:
            fire(f"MOVE STOP TO BREAKEVEN ({entry:.2f}) — "
                 f"+{RISK.breakeven_after_r_multiple}R closed")
            pos.at[i, "stop_current"] = max(stop, entry)
            pos.at[i, "breakeven_moved"] = True

        # 4. trading lot trail (after partial): daily close < 50-DMA
        sma50 = row.get(f"sma_{RISK.trailing_ma_period}")
        if (_bool(pos.at[i, "trading_open"]) and _bool(pos.at[i, "partial_taken"])
                and pd.notna(sma50) and row["close"] < sma50):
            fire(f"TRADING LOT EXIT — closed {row['close']:.2f} below 50-DMA {sma50:.2f}")
            book("trading", shares_trading - partial_shares, row["close"],
                 "trading-lot trail: close < 50-DMA")
            pos.at[i, "trading_open"] = False

        # 5. core lot: last COMPLETED week's close below the 150d SMA
        # (robust to holiday Fridays — a week whose Friday label is still in
        # the future is incomplete and ignored; Monday catches a bad prior
        # week even if Friday was a holiday)
        if _bool(pos.at[i, "core_open"]):
            wk_period = df["date"].dt.to_period("W-FRI")
            current_period = wk_period.iloc[-1]
            is_friday = pd.Timestamp(row["date"]).weekday() == 4
            completed = df[(wk_period < current_period)
                           | (is_friday & (wk_period == current_period))]
            if len(completed):
                wl = completed.iloc[-1]  # last daily bar of last completed week
                wl_sma = wl.get(f"sma_{RISK.core_exit_ma_period}")
                if pd.notna(wl_sma) and wl["close"] < wl_sma:
                    fire(f"CORE LOT EXIT — weekly close {wl['close']:.2f} "
                         f"(w/e {pd.Timestamp(wl['date']).date()}) below "
                         f"30-week MA {wl_sma:.2f} (the trend is over)")
                    book("core", int(p["shares_core"]), wl["close"],
                         "core exit: weekly close < 30-week MA", when=wl["date"])
                    pos.at[i, "core_open"] = False

    pos.to_csv(positions_path, index=False)
    if ledger_path:
        append_ledger(ledger_path, ledger_rows)
    return alerts, journal_rows
